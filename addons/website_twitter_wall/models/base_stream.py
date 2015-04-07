# -*- coding: utf-8 -*-
from httplib import HTTPConnection, HTTPSConnection
from logging import getLogger
from socket import timeout
from ssl import SSLError
from threading import Thread
from time import sleep
from urllib2 import quote

_logger = getLogger(__name__)

STREAM_VERSION = '1.1'


class StreamListener(object):

    def __init__(self, api=None):
        pass

    def on_connect(self):
        """Called once connected to streaming server.

        This will be invoked once a successful response
        is received from the server. Allows the listener
        to perform some work prior to entering the read loop.
        """
        _logger.info('Stream Connect to Twitter API')
        pass

    def on_data(self, raw_data):
        """Called when raw data is received from connection.

        Override this method if you wish to manually handle
        the stream data. Return False to stop stream and close connection.
        """
        pass

    def on_status(self, status):
        """Called when a new status arrives"""
        return

    def on_exception(self, exception):
        """Called when an unhandled exception occurs."""
        return

    def on_delete(self, status_id, user_id):
        """Called when a delete notice arrives for a status"""
        return

    def on_event(self, status):
        """Called when a new event arrives"""
        return

    def on_direct_message(self, status):
        """Called when a new direct message arrives"""
        return

    def on_limit(self, track):
        """Called when a limitation notice arrvies"""
        return

    def on_error(self, status_code):
        """Called when a non-200 status code is returned"""
        _logger.error('Stream Error :%s' % (status_code))
        return False

    def on_timeout(self):
        """Called when stream connection times out"""
        return

    def on_disconnect(self, notice):
        """Called when twitter sends a disconnect notice
        Disconnect codes are listed here:
        https://dev.twitter.com/docs/streaming-apis/messages#Disconnect_messages_disconnect
        """
        if notice:
            _logger.info(notice)
        return


class Stream(object):

    host = 'stream.twitter.com'

    def __init__(self, auth, listener, **options):
        self.auth = auth
        self.listener = listener
        self.running = False
        self.timeout = options.get("timeout", 300.0)
        self.retry_count = options.get("retry_count")
        self.retry_time_start = options.get("retry_time", 5.0)
        self.retry_420_start = options.get("retry_420", 60.0)
        self.retry_time_cap = options.get("retry_time_cap", 320.0)
        self.snooze_time_step = options.get("snooze_time", 0.25)
        self.snooze_time_cap = options.get("snooze_time_cap", 16)
        self.buffer_size = options.get("buffer_size",  1500)
        if options.get("secure", True):
            self.scheme = "https"
        else:
            self.scheme = "http"

        self.headers = options.get("headers") or {}
        self.parameters = None
        self.body = None
        self.retry_time = self.retry_time_start
        self.snooze_time = self.snooze_time_step

    def _run(self):
        # Authenticate
        url = "%s://%s%s" % (self.scheme, self.host, self.url)

        # Connect and process the stream
        error_counter = 0
        conn = None
        exception = None
        while self.running:
            if self.retry_count is not None and error_counter > self.retry_count:
                # quit if error count greater than retry count
                break
            try:
                if self.scheme == "http":
                    conn = HTTPConnection(self.host, timeout=self.timeout)
                else:
                    conn = HTTPSConnection(self.host, timeout=self.timeout)
                self.headers['Authorization'] = str(self.auth._generate_header(url.split('?')[0], 'HMAC-SHA1', '1.0', params=self.parameters))
                conn.connect()
                conn.request('POST', self.url, self.body, headers=self.headers)
                resp = conn.getresponse()
                if resp.status != 200:
                    if self.listener.on_error(resp.status) is False:
                        break
                    error_counter += 1
                    if resp.status == 420:
                        self.retry_time = max(self.retry_420_start, self.retry_time)
                    sleep(self.retry_time)
                    self.retry_time = min(self.retry_time * 2, self.retry_time_cap)
                else:
                    error_counter = 0
                    self.retry_time = self.retry_time_start
                    self.snooze_time = self.snooze_time_step
                    self.listener.on_connect()
                    self._read_loop(resp)
            except (timeout, SSLError) as exc:
                # If it's not time out treat it like any other exception
                if isinstance(exc, SSLError) and not (exc.args and 'timed out' in str(exc.args[0])):
                    exception = exc
                    break

                if self.listener.on_timeout() is False:
                    break
                if self.running is False:
                    break
                conn.close()
                sleep(self.snooze_time)
                self.snooze_time = min(self.snooze_time + self.snooze_time_step,
                                       self.snooze_time_cap)
            except Exception as exception:
                # any other exception is fatal, so kill loop
                break
        # cleanup
        self.running = False
        if not self.running:
            self.listener.on_disconnect(None)
        if conn:
            conn.close()

        if exception:
            # call a handler first so that the exception can be logged.
            self.listener.on_exception(exception)
            raise

    def _data(self, data):
        if self.listener.on_data(data) is False:
            self.running = False

    def _read_loop(self, resp):

        while self.running and not resp.isclosed():
            # Note: keep-alive newlines might be inserted before each length value.
            # read until we get a digit...
            c = '\n'
            while c == '\n' and self.running and not resp.isclosed():
                c = resp.read(1)
            delimited_string = c

            # read rest of delimiter length..
            d = ''
            while d != '\n' and self.running and not resp.isclosed():
                d = resp.read(1)
                delimited_string += d

            # read the next twitter status object
            if delimited_string.strip().isdigit():
                next_status_obj = resp.read(int(delimited_string))
                if self.running:
                    self._data(next_status_obj)

        if resp.isclosed():
            self.on_closed(resp)

    def _start(self, async):
        self.running = True
        if async:
            Thread(target=self._run).start()
        else:
            self._run()

    def on_closed(self, resp):
        """ Called when the response has been closed by Twitter """
        pass

    def filter(self, follow=None, track=None, async=False, locations=None, stall_warnings=False, languages=None, encoding='utf8'):
        self.parameters = {}
        self.headers['Content-type'] = "application/x-www-form-urlencoded"
        if self.running:
            _logger.error('Stream object already connected!')
        self.url = '/%s/statuses/filter.json?delimited=length' % STREAM_VERSION
        if follow:
            encoded_follow = [s.encode(encoding) for s in follow]
            self.parameters['follow'] = ','.join(encoded_follow)
        if track:
            encoded_track = [s.encode(encoding) for s in track]
            self.parameters['track'] = ','.join(encoded_track)
        if locations and len(locations) > 0:
            assert len(locations) % 4 == 0
            self.parameters['locations'] = ','.join(['%.4f' % l for l in locations])
        if stall_warnings:
            self.parameters['stall_warnings'] = stall_warnings
        if languages:
            self.parameters['language'] = ','.join(map(str, languages))
        self.body = '&'.join(['%s=%s' % (quote(str(k), ''), quote(str(v), '')) for k, v in self.parameters.iteritems()])
        self.parameters['delimited'] = 'length'
        self._start(async)

    def disconnect(self):
        if self.running is False:
            return
        self.listener.on_disconnect('Stream Disconnect from Twitter API')
        self.running = False
