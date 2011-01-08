import unittest

from . import IRCTestCase, make_suite
from tirsk.tirsk import IRCStream


class ConnectionTest(IRCTestCase):
    @IRCTestCase.exchange((('NICK mybot', 'OK'),))
    def test_simple_connection(self):
        def do_test():
            stream.connect(connection_done)
            self.wait()

        def connection_done(result):
            assert result

        stream = IRCStream('mybot', 'irc://localhost/', self.io_loop)
        self.io_loop.add_callback(do_test)
        self.io_loop.start()

def suite():
    return make_suite(ConnectionTest)
