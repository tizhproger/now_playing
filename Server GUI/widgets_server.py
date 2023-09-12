import http.server
import socketserver

server = ''
running = True

# The main behavior function for this server
def run_widgets(port):
    global server, running
    try:
        Handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", port), Handler) as httpd:
            print("Serving widgets on port " + str(port))
            server = httpd
            while running:
                httpd.handle_request()

    # Handle disconnecting clients 
    except Exception as e:
        print(str(e))


def close_widgets():
    global server, running

    running = False
    server.server_close()