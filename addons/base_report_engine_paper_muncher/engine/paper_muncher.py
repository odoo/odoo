# Part of Odoo. See LICENSE file for full copyright and licensing details.

import subprocess
import io

from .http import HttpResponse, HttpRequest
from .loader import OdooLoader
from .utils import binary


class PaperMuncher:

    __slots__ = ('loader',)

    loader: OdooLoader
    binary: str = binary

    def __init__(self, env, document, doc_name):
        self.loader = OdooLoader(env, document, doc_name)

    def _run(self, mode, *args: list[str]) -> tuple[bytes, str, Exception]:
        def sendResponse(stdin: io.TextIOWrapper, response: HttpResponse):
            stdin.write(bytes(response))
            stdin.flush()
        with subprocess.Popen(
            [self.binary, mode, *args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as process:

            stdout = process.stdout
            if stdout is None:
                raise RuntimeError("Outout from paper-muncher is None")

            stderr = process.stderr
            if stderr is None:
                raise RuntimeError("Error from paper-muncher is None")

            stdin = process.stdin
            if stdin is None:
                raise RuntimeError("Input from paper-muncher is None")

            try:
                while True:
                    request = HttpRequest()
                    request.readHeader(stdout)
                    if request.method == 'POST':
                        payload = request.readChunkedBody(stdout)
                        process.terminate()
                        return payload, stderr.read().decode('utf-8'), None

                    if request.method == 'GET':
                        try:
                            asset = self.loader.handleRequest(request.path)
                            response = HttpResponse(200)
                        except FileNotFoundError:
                            response = HttpResponse(404)
                        else:
                            response.addBody(asset)
                        sendResponse(stdin, response)
                        continue
                    break

            except Exception as e:  # noqa: BLE001
                process.terminate()
                return None, stderr.read().decode('utf-8'), e
            return None, stderr.read().decode('utf-8'), None

    @staticmethod
    def _construct_args(*args, **kwargs):
        extra_args = args
        for kwarg_name, kwarg_value in kwargs.items():
            extra_args += (f"--{kwarg_name}", str(kwarg_value))
        return extra_args

    def print(self, *args, **kwargs):
        args = self._construct_args(*args, **kwargs)
        return self._run('print', *args)

    def render(self, *args, **kwargs):
        args = self._construct_args(*args, **kwargs)
        return self._run('render', *args)
