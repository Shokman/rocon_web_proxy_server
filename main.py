import os
import sys
import traceback
import base64
import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.websocket import WebSocketHandler
from tornado.web import asynchronous
import json

# Global ID seed for clients
clients_connected = 0
proxy = None
clients = []
connToClient = None


class HttpHandler(tornado.web.RequestHandler):
    @asynchronous
    def get(self):
        global proxy, connToClient

        print "Got get"
        #TODO SET HEADER

        self.clear()
        self.set_status(200)
        self.set_header('server', 'example')
        self.set_header('connection', 'close')
        self.set_header('pragma', 'no-cache')
        self.set_header('cache-control', 'no-cache, no-store, must-revalidate,'
                        'pre-check=0, post-check=0, max-age=0')
        self.set_header('access-control-allow-origin', '*')
        self.set_header('content-type', 'multipart/x-mixed-replace;boundary='
                        '--boundarydonotcross')
        if proxy is not None:
            connToClient = self
            proxy.write_message('{"op":"video"}')


class RosbridgeProxyHandler(WebSocketHandler):
    def open(self):
        global clients_connected, authenticate, proxy, clients
        clients_connected += 1
        print "Client connected.  %d clients total." % clients_connected
        clients.append(self)

    def on_message(self, message):
        global proxy, clients, connToClient
        try:
            #print "Got message: [%s]" % str(message)
            msg = json.loads(message)
            if msg['op'] == 'proxy':
                proxy = self
                print "It's a proxy!"
            elif msg['op'] == 'video':
                if connToClient is not None:
                    if not connToClient.request.connection.stream.closed():
                        decoded = base64.b64decode(msg['data'])
                        connToClient.write(decoded)
                        connToClient.flush()
                    else:
                        self.write_message('{"op":"endVideo"}')
            elif msg['op'] == 'endVideo':
                if connToClient is not None:
                    connToClient.finish()
                    print "Connection Finished"

            if self == proxy:
                for client in clients:
                    if client != proxy:
                        client.write_message(message)
            else:
                if proxy is not None:
                    proxy.write_message(message)
        except:
            print "Unexpected error:", sys.exc_info()[0]
            traceback.print_exc()

    def on_close(self):
        global clients_connected, proxy
        clients_connected = clients_connected - 1
        print "Client disconnected. %d clients total." % clients_connected
        clients.remove(self)
        if self == proxy:
            proxy = None

    def check_origin(self, origin):
        return True


def main():
    application = tornado.web.Application([
        (r"/stream", HttpHandler),
        (r"/ws", RosbridgeProxyHandler),
        (r"/(.*)", tornado.web.StaticFileHandler, {"path": "./www"}),
    ])
    http_server = tornado.httpserver.HTTPServer(application)
    port = int(os.environ.get("PORT", 9090))
    http_server.listen(port)

    print "ROCON Web Proxy Server started on port %d" % port

    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
