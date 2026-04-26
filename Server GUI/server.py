import asyncio
import logging
import json
import websockets
import threading, asyncio
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError


clients = set()     # all clients
senders = set()     # data sources (extension)
receivers = set()   # OBS-widgets etc.
_exit_future = None

# ---------- LOGS ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NowPlayingWS")
logger.setLevel(logging.INFO)

_loop = None
_exit_future = None


async def handle_client(ws: websockets.WebSocketServerProtocol):
    """Procesing one websocket-client."""
    logger.info("[WS] client connected from %s", ws.remote_address)
    clients.add(ws)
    role = None  # 'sender' or 'receiver'

    try:
        async for message in ws:
            try:
                # --- ignoring binaries ---
                if isinstance(message, (bytes, bytearray)):
                    continue

                msg = message.strip()

                # --- registering OBS-widget ---
                if msg == "obs-source":
                    receivers.add(ws)
                    role = role or "receiver"
                    logger.info("[WS] OBS source registered")
                    continue
                
                # --- registering Twitch bot ---
                if msg == "connected - twitch bot":
                    receivers.add(ws)
                    role = role or "receiver"
                    logger.info("[WS] Twitch bot registered")
                    continue

                # --- markers from extension ---
                if msg.startswith("connected -"):
                    src = msg.split("connected -", 1)[1].strip() or "unknown"
                    senders.add(ws)
                    role = role or "sender"
                    logger.info("%s connected", src)
                    continue

                if msg.startswith("closed -"):
                    src = msg.split("closed -", 1)[1].strip() or "unknown"
                    logger.info("%s closed", src)
                    continue

                # --- trying to decode JSON with data about song ---
                try:
                    data = json.loads(msg)
                except json.JSONDecodeError:
                    print("JSON invalid")
                    # Not JSON — just ignore
                    logger.debug("Non-JSON message ignored: %r", msg[:80])
                    continue

                # If JSON is valid — considering it as a source
                if ws not in senders:
                    senders.add(ws)
                    role = role or "sender"

                # --- sending JSON to all OBS-widgets ---
                if receivers:
                    payload = json.dumps(data)
                    for r in list(receivers):
                        try:
                            await r.send(payload)
                        except Exception as e:
                            print("SEND ERROR:", repr(e))
                            logger.warning("Error sending to receiver: %s", e)
                            receivers.discard(r)

            except Exception as e:
                # Any exception during one message shoud not break a connection
                logger.error("Error while handling message: %s", e, exc_info=True)
                continue

    except (ConnectionClosedOK, ConnectionClosedError) as e:
        logger.info(
            "[WS] connection closed: code=%s reason=%s",
            getattr(e, "code", "?"),
            getattr(e, "reason", ""),
        )
    except Exception as e:
        logger.error("Unhandled error in handle_client: %s", e, exc_info=True)
    finally:
        clients.discard(ws)
        senders.discard(ws)
        receivers.discard(ws)
        logger.info("[WS] client disconnected; role=%s", role)


async def echo_server(host: str, port: int, exit_future: asyncio.Future):
    """Start of websocket-server and waiting exit signal."""
    async with websockets.serve(
        handle_client, host, port,
        ping_interval=20,
        ping_timeout=20
    ):
        logger.info("[WS] Server started on %s:%s", host, port)
        await exit_future
        logger.info("[WS] exit signal received, stopping server")


def _loop_exception_filter(loop, context):
    msg = context.get("exception", context.get("message"))
    logger.error("Asyncio error: %s", msg)


def run_webserver(ipaddress: str, port: int):
    global _loop, _exit_future, clients, senders, receivers

    # to avoid junk on reboot
    clients.clear()
    senders.clear()
    receivers.clear()

    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _loop.set_exception_handler(_loop_exception_filter)

    _exit_future = _loop.create_future()

    try:
        # IMPORTANT: run_until_complete guarantees normal exit from async with serve(...)
        _loop.run_until_complete(echo_server(ipaddress, int(port), _exit_future))
    finally:
        # safely cutting all tails
        pending = asyncio.all_tasks(_loop)
        for t in pending:
            t.cancel()
        _loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        _loop.close()
        _loop = None
        _exit_future = None


def close_webserver():
    global _loop, _exit_future
    if _loop and _exit_future and not _exit_future.done():
        # thread-safe signal in loop of a server
        _loop.call_soon_threadsafe(_exit_future.set_result, "exit")
