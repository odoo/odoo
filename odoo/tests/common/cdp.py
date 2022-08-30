import base64
import concurrent.futures
import itertools
import json
import logging
import os.path
import pathlib
import platform
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import unittest
from concurrent.futures import Future, CancelledError, wait
from datetime import datetime

import requests
import werkzeug.urls

import odoo.tools
from odoo.tools.misc import find_in_path

from .utils import HOST, get_db_name

try:
    from concurrent.futures import InvalidStateError
except ImportError:
    InvalidStateError = NotImplementedError
try:
    import websocket
except ImportError:
    # chrome headless tests will be skipped
    websocket = None

CHECK_BROWSER_SLEEP = 0.1 # seconds
CHECK_BROWSER_ITERATIONS = 100
BROWSER_WAIT = CHECK_BROWSER_SLEEP * CHECK_BROWSER_ITERATIONS # seconds

_logger = logging.getLogger(__name__)
class ChromeBrowserException(Exception):
    pass

def fmap(future, map_fun):
    """Maps a future's result through a callback.

    Resolves to the application of ``map_fun`` to the result of ``future``.

    .. warning:: this does *not* recursively resolve futures, if that's what
                 you need see :func:`fchain`
    """
    fmap_future = Future()
    @future.add_done_callback
    def _(f):
        try:
            fmap_future.set_result(map_fun(f.result()))
        except Exception as e:
            fmap_future.set_exception(e)
    return fmap_future

def fchain(future, next_callback):
    """Chains a future's result to a new future through a callback.

    Corresponds to the ``bind`` monadic operation (aka flatmap aka then...
    kinda).
    """
    new_future = Future()
    @future.add_done_callback
    def _(f):
        try:
            n = next_callback(f.result())
            @n.add_done_callback
            def _(f):
                try:
                    new_future.set_result(f.result())
                except Exception as e:
                    new_future.set_exception(e)

        except Exception as e:
            new_future.set_exception(e)

    return new_future

class ChromeBrowser:
    """ Helper object to control a Chrome headless process. """
    remote_debugging_port = 0  # 9222, change it in a non-git-tracked file

    def __init__(self, test_class):
        self._logger = test_class._logger
        self.test_class = test_class
        if websocket is None:
            self._logger.warning("websocket-client module is not installed")
            raise unittest.SkipTest("websocket-client module is not installed")
        self.devtools_port = None
        self.ws_url = ''  # WebSocketUrl
        self.ws = None  # websocket
        self.user_data_dir = tempfile.mkdtemp(suffix='_chrome_odoo')
        self.chrome_pid = None

        otc = odoo.tools.config
        self.screenshots_dir = os.path.join(otc['screenshots'], get_db_name(), 'screenshots')
        self.screencasts_dir = None
        self.screencasts_frames_dir = None
        if otc['screencasts']:
            self.screencasts_dir = os.path.join(otc['screencasts'], get_db_name(), 'screencasts')
            self.screencasts_frames_dir = os.path.join(self.screencasts_dir, 'frames')
            os.makedirs(self.screencasts_frames_dir, exist_ok=True)
        self.screencast_frames = []
        os.makedirs(self.screenshots_dir, exist_ok=True)

        self.window_size = test_class.browser_size
        self.touch_enabled = test_class.touch_enabled
        self.sigxcpu_handler = None
        self._chrome_start()
        self._find_websocket()
        self._logger.info('Websocket url found: %s', self.ws_url)
        self._open_websocket()
        self._request_id = itertools.count()
        self._result = Future()
        # maps request_id to Futures
        self._responses = {}
        # maps frame ids to callbacks
        self._frames = {}
        self._handlers = {
            'Runtime.consoleAPICalled': self._handle_console,
            'Runtime.exceptionThrown': self._handle_exception,
            'Page.frameStoppedLoading': self._handle_frame_stopped_loading,
            'Page.screencastFrame': self._handle_screencast_frame,
        }
        self._receiver = threading.Thread(
            target=self._receive,
            name="WebSocket events consumer",
            args=(get_db_name(),)
        )
        self._receiver.start()
        self._logger.info('Enable chrome headless console log notification')
        self._websocket_send('Runtime.enable')
        self._logger.info('Chrome headless enable page notifications')
        self._websocket_send('Page.enable')
        if os.name == 'posix':
            self.sigxcpu_handler = signal.getsignal(signal.SIGXCPU)
            signal.signal(signal.SIGXCPU, self.signal_handler)

    def signal_handler(self, sig, frame):
        if sig == signal.SIGXCPU:
            _logger.info('CPU time limit reached, stopping Chrome and shutting down')
            self.stop()
            os._exit(0)

    def stop(self):
        if self.chrome_pid is not None:
            self._logger.info("Closing chrome headless with pid %s", self.chrome_pid)
            self._websocket_send('Browser.close')
            self._logger.info("Closing websocket connection")
            self.ws.close()
            self._logger.info("Terminating chrome headless with pid %s", self.chrome_pid)
            os.kill(self.chrome_pid, signal.SIGTERM)
        if self.user_data_dir and os.path.isdir(self.user_data_dir) and self.user_data_dir != '/':
            self._logger.info('Removing chrome user profile "%s"', self.user_data_dir)
            shutil.rmtree(self.user_data_dir, ignore_errors=True)
        # Restore previous signal handler
        if self.sigxcpu_handler and os.name == 'posix':
            signal.signal(signal.SIGXCPU, self.sigxcpu_handler)

    @property
    def executable(self):
        system = platform.system()
        if system == 'Linux':
            for bin_ in ['google-chrome', 'chromium', 'chromium-browser', 'google-chrome-stable']:
                try:
                    return find_in_path(bin_)
                except IOError:
                    continue

        elif system == 'Darwin':
            bins = [
                '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                '/Applications/Chromium.app/Contents/MacOS/Chromium',
            ]
            for bin_ in bins:
                if os.path.exists(bin_):
                    return bin_

        elif system == 'Windows':
            bins = [
                '%ProgramFiles%\\Google\\Chrome\\Application\\chrome.exe',
                '%ProgramFiles(x86)%\\Google\\Chrome\\Application\\chrome.exe',
                '%LocalAppData%\\Google\\Chrome\\Application\\chrome.exe',
            ]
            for bin_ in bins:
                bin_ = os.path.expandvars(bin_)
                if os.path.exists(bin_):
                    return bin_

        raise unittest.SkipTest("Chrome executable not found")

    def _chrome_without_limit(self, cmd):
        if os.name == 'posix' and platform.system() != 'Darwin':
            # since the introduction of pointer compression in Chrome 80 (v8 v8.0),
            # the memory reservation algorithm requires more than 8GiB of
            # virtual mem for alignment this exceeds our default memory limits.
            def preexec():
                import resource
                resource.setrlimit(resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        else:
            preexec = None

        # pylint: disable=subprocess-popen-preexec-fn
        return subprocess.Popen(cmd, stderr=subprocess.DEVNULL, preexec_fn=preexec)

    def _spawn_chrome(self, cmd):
        proc = self._chrome_without_limit(cmd)
        port_file = pathlib.Path(self.user_data_dir, 'DevToolsActivePort')
        for _ in range(CHECK_BROWSER_ITERATIONS):
            time.sleep(CHECK_BROWSER_SLEEP)
            if port_file.is_file() and port_file.stat().st_size > 5:
                with port_file.open('r', encoding='utf-8') as f:
                    self.devtools_port = int(f.readline())
                    return proc.pid
        raise unittest.SkipTest(f'Failed to detect chrome devtools port after {BROWSER_WAIT :.1f}s.')

    def _chrome_start(self):
        if self.chrome_pid is not None:
            return

        switches = {
            '--headless': '',
            '--no-default-browser-check': '',
            '--no-first-run': '',
            '--disable-extensions': '',
            '--disable-background-networking' : '',
            '--disable-background-timer-throttling' : '',
            '--disable-backgrounding-occluded-windows': '',
            '--disable-renderer-backgrounding' : '',
            '--disable-breakpad': '',
            '--disable-client-side-phishing-detection': '',
            '--disable-crash-reporter': '',
            '--disable-default-apps': '',
            '--disable-dev-shm-usage': '',
            '--disable-device-discovery-notifications': '',
            '--disable-namespace-sandbox': '',
            '--user-data-dir': self.user_data_dir,
            '--disable-translate': '',
            # required for tours that use Youtube autoplay conditions (namely website_slides' "course_tour")
            '--autoplay-policy': 'no-user-gesture-required',
            '--window-size': self.window_size,
            '--remote-debugging-address': HOST,
            '--remote-debugging-port': str(self.remote_debugging_port),
            '--no-sandbox': '',
            '--disable-gpu': '',
        }
        if self.touch_enabled:
            # enable Chrome's Touch mode, useful to detect touch capabilities using
            # "'ontouchstart' in window"
            switches['--touch-events'] = ''

        cmd = [self.executable]
        cmd += ['%s=%s' % (k, v) if v else k for k, v in switches.items()]
        url = 'about:blank'
        cmd.append(url)
        try:
            self.chrome_pid = self._spawn_chrome(cmd)
        except OSError:
            raise unittest.SkipTest("%s not found" % cmd[0])
        self._logger.info('Chrome pid: %s', self.chrome_pid)

    def _find_websocket(self):
        version = self._json_command('version')
        self._logger.info('Browser version: %s', version['Browser'])
        infos = self._json_command('', get_key=0)  # Infos about the first tab
        self.ws_url = infos['webSocketDebuggerUrl']
        self.dev_tools_frontend_url = infos.get('devtoolsFrontendUrl')
        self._logger.info('Chrome headless temporary user profile dir: %s', self.user_data_dir)

    def _json_command(self, command, timeout=3, get_key=None):
        """Queries browser state using JSON

        Available commands:

        ``''``
            return list of tabs with their id
        ``list`` (or ``json/``)
            list tabs
        ``new``
            open a new tab
        :samp:`activate/{id}`
            activate a tab
        :samp:`close/{id}`
            close a tab
        ``version``
            get chrome and dev tools version
        ``protocol``
            get the full protocol
        """
        command = '/'.join(['json', command]).strip('/')
        url = werkzeug.urls.url_join('http://%s:%s/' % (HOST, self.devtools_port), command)
        self._logger.info("Issuing json command %s", url)
        delay = 0.1
        tries = 0
        failure_info = None
        while timeout > 0:
            try:
                os.kill(self.chrome_pid, 0)
            except ProcessLookupError:
                message = 'Chrome crashed at startup'
                break
            try:
                r = requests.get(url, timeout=3)
                if r.ok:
                    res = r.json()
                    if get_key is None:
                        return res
                    else:
                        return res[get_key]
            except requests.ConnectionError as e:
                failure_info = str(e)
                message = 'Connection Error while trying to connect to Chrome debugger'
            except requests.exceptions.ReadTimeout as e:
                failure_info = str(e)
                message = 'Connection Timeout while trying to connect to Chrome debugger'
                break
            except (KeyError, IndexError):
                message = 'Key "%s" not found in json result "%s" after connecting to Chrome debugger' % (get_key, res)
            time.sleep(delay)
            timeout -= delay
            delay = delay * 1.5
            tries += 1
        self._logger.error("%s after %s tries" % (message, tries))
        if failure_info:
            self._logger.info(failure_info)
        self.stop()
        raise unittest.SkipTest("Error during Chrome headless connection")

    def _open_websocket(self):
        self.ws = websocket.create_connection(self.ws_url, enable_multithread=True)
        if self.ws.getstatus() != 101:
            raise unittest.SkipTest("Cannot connect to chrome dev tools")
        self.ws.settimeout(0.01)

    def _receive(self, dbname):
        threading.current_thread().dbname = dbname
        # So CDT uses a streamed JSON-RPC structure, meaning a request is
        # {id, method, params} and eventually a {id, result | error} should
        # arrive the other way, however for events it uses "notifications"
        # meaning request objects without an ``id``, but *coming from the server
        while True: # or maybe until `self._result` is `done()`?
            try:
                msg = self.ws.recv()
                self._logger.debug('\n<- %s', msg)
            except websocket.WebSocketTimeoutException:
                continue
            except Exception:
                # if the socket is still connected something bad happened,
                # otherwise the client was just shut down
                self._result.cancel()
                if self.ws.connected:
                    raise
                return

            res = json.loads(msg)
            request_id = res.get('id')
            try:
                if request_id is None:
                    handler = self._handlers.get(res['method'])
                    if handler:
                        handler(**res['params'])
                else:
                    f = self._responses.pop(request_id, None)
                    if f:
                        if 'result' in res:
                            f.set_result(res['result'])
                        else:
                            f.set_exception(ChromeBrowserException(res['error']['message']))
            except Exception:
                _logger.exception("While processing message %s", msg)

    def _websocket_request(self, method, *, params=None, timeout=10.0):
        assert threading.get_ident() != self._receiver.ident,\
            "_websocket_request must not be called from the consumer thread"
        if self.ws is None:
            return

        f = self._websocket_send(method, params=params, with_future=True)
        try:
            return f.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f'{method}({params or ""})')

    def _websocket_send(self, method, *, params=None, with_future=False):
        """send chrome devtools protocol commands through websocket

        If ``with_future`` is set, returns a ``Future`` for the operation.
        """
        if self.ws is None:
            return

        result = None
        request_id = next(self._request_id)
        if with_future:
            result = self._responses[request_id] = Future()
        payload = {'method': method, 'id': request_id}
        if params:
            payload['params'] = params
        self._logger.debug('\n-> %s', payload)
        self.ws.send(json.dumps(payload))
        return result

    def _handle_console(self, type, args=None, stackTrace=None, **kw): # pylint: disable=redefined-builtin
        # console formatting differs somewhat from Python's, if args[0] has
        # format modifiers that many of args[1:] get formatted in, missing
        # args are replaced by empty strings and extra args are concatenated
        # (space-separated)
        #
        # current version modifies the args in place which could and should
        # probably be improved
        if args:
            arg0, args = str(self._from_remoteobject(args[0])), args[1:]
        else:
            arg0, args = '', []
        formatted = [re.sub(r'%[%sdfoOc]', self.console_formatter(args), arg0)]
        # formatter consumes args it uses, leaves unformatted args untouched
        formatted.extend(str(self._from_remoteobject(arg)) for arg in args)
        message = ' '.join(formatted)
        stack = ''.join(self._format_stack({'type': type, 'stackTrace': stackTrace}))
        if stack:
            message += '\n' + stack

        log_type = type
        self._logger.getChild('browser').log(
            self._TO_LEVEL.get(log_type, logging.INFO),
            "%s", message # might still have %<x> characters
        )

        if log_type == 'error':
            self.take_screenshot()
            self._save_screencast()
            try:
                self._result.set_exception(ChromeBrowserException(message))
            except CancelledError:
                ...
            except InvalidStateError:
                self._logger.warning(
                    "Trying to set result to failed (%s) but found the future settled (%s)",
                    message, self._result
                )
        elif 'test successful' in message:
            if self.test_class.allow_end_on_form:
                self._result.set_result(True)
                return

            qs = fchain(
                self._websocket_send('DOM.getDocument', params={'depth': 0}, with_future=True),
                lambda d: self._websocket_send("DOM.querySelector", params={
                    'nodeId': d['root']['nodeId'],
                    'selector': '.o_form_editable',
                }, with_future=True)
            )
            @qs.add_done_callback
            def _qs_result(fut):
                # stupid dumbass chrome returns a nodeid of 0 when nothing
                # is found
                if fut.result()['nodeId']:
                    self.take_screenshot("unsaved_form_")
                    self._result.set_exception(ChromeBrowserException("""\
Tour finished with an open form view in edition mode.

Form views in edition mode are automatically saved when the page is closed, \
which leads to stray network requests and inconsistencies."""))
                    return

                try:
                    self._result.set_result(True)
                except Exception:
                    # if the future was already failed, we're happy,
                    # otherwise swap for a new failed
                    if self._result.exception() is None:
                        self._result = Future()
                        self._result.set_exception(ChromeBrowserException(
                            "Tried to make the tour successful twice."
                        ))


    def _handle_exception(self, exceptionDetails, timestamp):
        message = exceptionDetails['text']
        exception = exceptionDetails.get('exception')
        if exception:
            message += str(self._from_remoteobject(exception))
        exceptionDetails['type'] = 'trace'  # fake this so _format_stack works
        stack = ''.join(self._format_stack(exceptionDetails))
        if stack:
            message += '\n' + stack

        self.take_screenshot()
        self._save_screencast()
        try:
            self._result.set_exception(ChromeBrowserException(message))
        except CancelledError:
            ...
        except InvalidStateError:
            self._logger.warning(
                "Trying to set result to failed (%s) but found the future settled (%s)",
                message, self._result
            )

    def _handle_frame_stopped_loading(self, frameId):
        wait = self._frames.pop(frameId, None)
        if wait:
            wait()

    def _handle_screencast_frame(self, sessionId, data, metadata):
        self._websocket_send('Page.screencastFrameAck', params={'sessionId': sessionId})
        outfile = os.path.join(self.screencasts_frames_dir, 'frame_%05d.b64' % len(self.screencast_frames))
        with open(outfile, 'w') as f:
            f.write(data)
            self.screencast_frames.append({
                'file_path': outfile,
                'timestamp': metadata.get('timestamp')
            })

    _TO_LEVEL = {
        'debug': logging.DEBUG,
        'log': logging.INFO,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        # TODO: what do with
        # dir, dirxml, table, trace, clear, startGroup, startGroupCollapsed,
        # endGroup, assert, profile, profileEnd, count, timeEnd
    }

    def take_screenshot(self, prefix='sc_', suffix=None):
        def handler(f):
            base_png = f.result(timeout=0)['data']
            if not base_png:
                self._logger.warning("Couldn't capture screenshot: expected image data, got ?? error ??")
                return

            decoded = base64.b64decode(base_png, validate=True)
            fname = '{}{:%Y%m%d_%H%M%S_%f}{}.png'.format(
                prefix, datetime.now(),
                suffix or '_%s' % self.test_class.__name__)
            full_path = os.path.join(self.screenshots_dir, fname)
            with open(full_path, 'wb') as f:
                f.write(decoded)
            self._logger.runbot('Screenshot in: %s', full_path)

        self._logger.info('Asking for screenshot')
        f = self._websocket_send('Page.captureScreenshot', with_future=True)
        f.add_done_callback(handler)
        return f

    def _save_screencast(self, prefix='failed'):
        # could be encododed with something like that
        #  ffmpeg -framerate 3 -i frame_%05d.png  output.mp4
        if not self.screencast_frames:
            self._logger.debug('No screencast frames to encode')
            return None

        for f in self.screencast_frames:
            with open(f['file_path'], 'rb') as b64_file:
                frame = base64.decodebytes(b64_file.read())
            os.unlink(f['file_path'])
            f['file_path'] = f['file_path'].replace('.b64', '.png')
            with open(f['file_path'], 'wb') as png_file:
                png_file.write(frame)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        fname = '%s_screencast_%s.mp4' % (prefix, timestamp)
        outfile = os.path.join(self.screencasts_dir, fname)

        try:
            ffmpeg_path = find_in_path('ffmpeg')
        except IOError:
            ffmpeg_path = None

        if ffmpeg_path:
            nb_frames = len(self.screencast_frames)
            concat_script_path = os.path.join(self.screencasts_dir, fname.replace('.mp4', '.txt'))
            with open(concat_script_path, 'w') as concat_file:
                for i in range(nb_frames):
                    frame_file_path = os.path.join(self.screencasts_frames_dir, self.screencast_frames[i]['file_path'])
                    end_time = time.time() if i == nb_frames - 1 else self.screencast_frames[i+1]['timestamp']
                    duration = end_time - self.screencast_frames[i]['timestamp']
                    concat_file.write("file '%s'\nduration %s\n" % (frame_file_path, duration))
                concat_file.write("file '%s'" % frame_file_path)  # needed by the concat plugin
            r = subprocess.run([ffmpeg_path, '-intra', '-f', 'concat','-safe', '0', '-i', concat_script_path, '-pix_fmt', 'yuv420p', outfile])
            self._logger.log(25, 'Screencast in: %s', outfile)
        else:
            outfile = outfile.strip('.mp4')
            shutil.move(self.screencasts_frames_dir, outfile)
            self._logger.runbot('Screencast frames in: %s', outfile)

    def start_screencast(self):
        assert self.screencasts_dir
        self._websocket_send('Page.startScreencast')

    def set_cookie(self, name, value, path, domain):
        params = {'name': name, 'value': value, 'path': path, 'domain': domain}
        self._websocket_request('Network.setCookie', params=params)
        return

    def delete_cookie(self, name, **kwargs):
        params = {k: v for k, v in kwargs.items() if k in ['url', 'domain', 'path']}
        params['name'] = name
        self._websocket_request('Network.deleteCookies', params=params)
        return

    def _wait_ready(self, ready_code, timeout=60):
        self._logger.info('Evaluate ready code "%s"', ready_code)
        start_time = time.time()
        result = None
        while True:
            taken = time.time() - start_time
            if taken > timeout:
                break

            result = self._websocket_request('Runtime.evaluate', params={
                'expression': "try { %s } catch {}" % ready_code,
                'awaitPromise': True,
            }, timeout=timeout-taken)['result']

            if result == {'type': 'boolean', 'value': True}:
                time_to_ready = time.time() - start_time
                if taken > 2:
                    self._logger.info('The ready code tooks too much time : %s', time_to_ready)
                return True

        self.take_screenshot(prefix='sc_failed_ready_')
        self._logger.info('Ready code last try result: %s', result)
        return False

    def _wait_code_ok(self, code, timeout):
        self._logger.info('Evaluate test code "%s"', code)
        start = time.time()
        res = self._websocket_request('Runtime.evaluate', params={
            'expression': code,
            'awaitPromise': True,
        }, timeout=timeout)['result']
        if res.get('subtype') == 'error':
            raise ChromeBrowserException("Running code returned an error: %s" % res)
        # if the runcode was a promise which took some time to execute, discount
        # that from the timeout
        if self._result.result(time.time() - start + timeout):
            return

        self.take_screenshot()
        self._save_screencast()
        raise ChromeBrowserException('Script timeout exceeded')


    def navigate_to(self, url, wait_stop=False):
        self._logger.info('Navigating to: "%s"', url)
        nav_result = self._websocket_request('Page.navigate', params={'url': url}, timeout=20.0)
        self._logger.info("Navigation result: %s", nav_result)
        if wait_stop:
            frame_id = nav_result['frameId']
            e = threading.Event()
            self._frames[frame_id] = e.set
            self._logger.info('Waiting for frame %r to stop loading', frame_id)
            e.wait(10)

    def clear(self):
        self._websocket_send('Page.stopScreencast')
        if self.screencasts_dir and os.path.isdir(self.screencasts_frames_dir):
            shutil.rmtree(self.screencasts_frames_dir)
        self.screencast_frames = []
        self._websocket_request('Page.stopLoading')
        self._websocket_request('Runtime.evaluate', params={'expression': """
        ('serviceWorker' in navigator) &&
            navigator.serviceWorker.getRegistrations().then(
                registrations => Promise.all(registrations.map(r => r.unregister()))
            )
        """, 'awaitPromise': True})
        # wait for the screenshot or whatever
        wait(self._responses.values(), 10)
        self._logger.info('Deleting cookies and clearing local storage')
        self._websocket_request('Network.clearBrowserCache')
        self._websocket_request('Network.clearBrowserCookies')
        self._websocket_request('Runtime.evaluate', params={'expression': 'try {localStorage.clear(); sessionStorage.clear();} catch(e) {}'})
        self.navigate_to('about:blank', wait_stop=True)
        # hopefully after navigating to about:blank there's no event left
        self._frames.clear()
        # wait for the clearing requests to finish in case the browser is re-used
        wait(self._responses.values(), 10)
        self._responses.clear()
        self._result.cancel()
        self._result = Future()

    def _from_remoteobject(self, arg):
        """ attempts to make a CDT RemoteObject comprehensible
        """
        objtype = arg['type']
        subtype = arg.get('subtype')
        if objtype == 'undefined':
            # the undefined remoteobject is literally just {type: undefined}...
            return 'undefined'
        elif objtype != 'object' or subtype not in (None, 'array'):
            # value is the json representation for json object
            # otherwise fallback on the description which is "a string
            # representation of the object" e.g. the traceback for errors, the
            # source for functions, ... finally fallback on the entire arg mess
            return arg.get('value', arg.get('description', arg))
        elif subtype == 'array':
            # apparently value is *not* the JSON representation for arrays
            # instead it's just Array(3) which is useless, however the preview
            # properties are the same as object which is useful (just ignore the
            # name which is the index)
            return '[%s]' % ', '.join(
                repr(p['value']) if p['type'] == 'string' else str(p['value'])
                for p in arg.get('preview', {}).get('properties', [])
                if re.match(r'\d+', p['name'])
            )
        # all that's left is type=object, subtype=None aka custom or
        # non-standard objects, print as TypeName(param=val, ...), sadly because
        # of the way Odoo widgets are created they all appear as Class(...)
        # nb: preview properties are *not* recursive, the value is *all* we get
        return '%s(%s)' % (
            arg.get('className') or 'object',
            ', '.join(
                '%s=%s' % (p['name'], repr(p['value']) if p['type'] == 'string' else p['value'])
                for p in arg.get('preview', {}).get('properties', [])
                if p.get('value') is not None
            )
        )

    LINE_PATTERN = '\tat %(functionName)s (%(url)s:%(lineNumber)d:%(columnNumber)d)\n'
    def _format_stack(self, logrecord):
        if logrecord['type'] not in ['trace']:
            return

        trace = logrecord.get('stackTrace')
        while trace:
            for f in trace['callFrames']:
                yield self.LINE_PATTERN % f
            trace = trace.get('parent')

    def console_formatter(self, args):
        """ Formats similarly to the console API:

        * if there are no args, don't format (return string as-is)
        * %% -> %
        * %c -> replace by styling directives (ignore for us)
        * other known formatters -> replace by corresponding argument
        * leftover known formatters (args exhausted) -> replace by empty string
        * unknown formatters -> return as-is
        """
        if not args:
            return lambda m: m[0]

        def replacer(m):
            fmt = m[0][1]
            if fmt == '%':
                return '%'
            if fmt in 'sdfoOc':
                if not args:
                    return ''
                repl = args.pop(0)
                if fmt == 'c':
                    return ''
                return str(self._from_remoteobject(repl))
            return m[0]
        return replacer
