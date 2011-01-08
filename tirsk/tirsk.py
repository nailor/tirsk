import functools
import socket
import urlparse

from tornado.iostream import IOStream
from tornado.ioloop import IOLoop

class IRCStream(object):
    """
    A connection to an IRC server utilizing IOStream
    """
    def __init__(self, nick, url, io_loop=None):
        self.nick = nick
        self.url = url
        self.io_loop = io_loop or IOLoop.instance()

        parsed = urlparse.urlsplit(self.url)
        assert parsed.scheme == 'irc'
        if ':' in parsed.netloc:
            host, _, port = parsed.netloc.partition(':')
            port = int(port)
        else:
            host = parsed.netloc
            port = 6667
        self.host = host
        self.port = port

    def connect(self, callback):
        self.stream = IOStream(socket.socket(), io_loop=self.io_loop)
        self.stream.connect((self.host, self.port),
                            functools.partial(self._on_connect, callback))


    def _on_connect(self, callback):
        self.stream.write('NICK %s\r\n' % self.nick)
        callback(True)
