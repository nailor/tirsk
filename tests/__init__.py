# This testing module borrows some parts from stango by Petri Lehtinen
# For more info see http://digip.org/stango

import contextlib
import errno
import fcntl
import functools
import logging
import socket
import sys
import unittest

from tornado.testing import AsyncTestCase
from tornado.ioloop import IOLoop
from tornado.iostream import IOStream
from tornado.stack_context import StackContext

class IRCTestServer(object):
    def __init__(self, io_loop, tester):
        self.io_loop = io_loop
        self.callback = None
        self.conn = None
        self.stream = None
        self.tester = tester

    def listen(self, host='localhost', port=6667):
        self.bind(host, port)
        self.start()

    def bind(self, host, port):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        flags = fcntl.fcntl(self._socket.fileno(), fcntl.F_GETFD)
        flags |= fcntl.FD_CLOEXEC
        fcntl.fcntl(self._socket.fileno(), fcntl.F_SETFD, flags)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.setblocking(0)
        self._socket.bind((host, port))
        self._socket.listen(5)

    def start(self):
        self.io_loop.add_handler(
            self._socket.fileno(), self._handle_events,
            IOLoop.READ)

    def stop(self):
        if self.conn:
            self.conn.finish()

        if self.stream:
            self.stream.close()

    def _handle_events(self, fd, events):
        while True:
            try:
                connection, address = self._socket.accept()
            except socket.error, e:
                if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                    return
                raise
            try:
                self.stream = IOStream(connection, io_loop=self.io_loop)
                self.conn = IRCConnection(self.stream, address, self.tester)
            except:
                logging.error("Error in connection callback", exc_info=True)

class IRCConnection(object):
    def __init__(self, stream, address, callback):
        self.stream = stream
        self.address = address
        self.callback = callback
        self.read_cmd()

    def read_cmd(self):
        self.stream.read_until('\r\n', self._cmd_received)

    def write(self, chunk, cb):
        self.stream.write(chunk, cb)

    def finish(self):
        self.stream.close()

    def _cmd_received(self, data):
        def _process_finish():
            if do_finish:
                self.finish()
            else:
                self.read_cmd()

        response, do_finish = self.callback(data)
        self.write(response, _process_finish)

class TestIOLoop(IOLoop):
    def handle_callback_exception(self, callback):
        # Override the default to cause the server side asserts to
        # fail the tests
        raise

class IRCTestCase(AsyncTestCase):
    def setup(self):
        pass

    def teardown(self):
        pass

    def eq(self, a, b):
        return self.assertEqual(a, b)

    def get_tester(self):
        # This returns default tester that verifies input agains
        # self._exchange, set by @exchange decorator.
        #
        # Usage is somewhat like this, note that CR-LF should be omitted:
        #
        # @exchange(('NICK bot', 'OK'), ('OTHERCMD', 'REPLY'))
        # def test_something(self):
        #     do_some_testing()
        #
        # This also verifies that the commands arrive at the specified
        # order
        def exchangetester(data):
            assert self._exchange
            cur = self._exchange[0]
            self._exchange = self._exchange[1:]

            self.eq(data, cur[0] + '\r\n')

            # By returning `not self._exchange` as second item in
            # tuple, we ensure that the connection is closed when the
            # server has no further things to say.
            if not self._exchange:
                self.stop()

            return (cur[1] + '\r\n', not self._exchange)
        return exchangetester

    # Don't override these. setUp and tearDown are just convenience
    # wrappers so that the classes subclassing IRCTestCase do not need
    # to do super calls
    def get_new_ioloop(self):
        return TestIOLoop()

    def setUp(self):
        super(IRCTestCase, self).setUp()
        self.setup()
        self._exchange = None
        self._tester = self.get_tester()

        @contextlib.contextmanager
        def _raiser_context():
            yield

        with StackContext(_raiser_context):
            self.server = IRCTestServer(self.io_loop, self._tester)
            self.server.listen('localhost', 6667)

    def tearDown(self):
        self.server.stop()
        super(IRCTestCase, self).tearDown()
        self.teardown()

    # Decorator to set the expected communication of a client
    @classmethod
    def exchange(cls, *exchange):
        def outer(func):
            @functools.wraps(func)
            def inner(self, *a, **kw):
                self._exchange = exchange
                func(self, *a, **kw)
                assert not self._exchange
            return inner
        return outer

def make_suite(cls):
    '''Makes a suite from all test functions in a TestCase class'''
    return unittest.TestLoader().loadTestsFromTestCase(cls)

def suite():
    from . import test_connection
    suite = unittest.TestSuite()
    suite.addTest(test_connection.suite())

    return suite

def run(verbose=False):
    return unittest.TextTestRunner(verbosity=(2 if verbose else 1)).run(suite())
