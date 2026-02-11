# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import MethodNotAllowed
import subprocess

try:
    import magic
except ImportError:
    magic = None

from .http import HttpResponse, HttpRequest
from .loader import OdooLoader
from .utils import binary


class PaperMuncher:

    __slots__ = ('loader',)

    loader: OdooLoader
    binary: str = binary

    def __init__(self, env, document, doc_name):
        self.loader = OdooLoader(env, document, doc_name)

    def _run(self, mode, *args: list[str]) -> bytes:
        # TODO: find a better way to handle the arg0 and output url
        with subprocess.Popen(
            [self.binary, '--sandbox', mode, args[0], '-o', 'http://stdout', *args[1:]],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        ) as process:
            stdout = process.stdout
            stdin = process.stdin
            while True:
                request = HttpRequest()
                request.readHeader(stdout)
                if request.method == 'PUT':
                    response = HttpResponse(200)
                    response.addBody(b'')
                    stdin.write(bytes(response))
                    stdin.flush()

                    pdf = stdout.read()
                    process.terminate()
                    return pdf

                if request.method == 'GET':
                    try:
                        asset = self.loader.handleRequest(request.path)
                        response = HttpResponse(200)
                        if magic is not None:
                            mime_type = magic.from_buffer(asset, mime=True)
                            response.addHeader('Content-Type', mime_type)
                    except FileNotFoundError:
                        response = HttpResponse(404)
                    else:
                        response.addBody(asset)
                    stdin.write(bytes(response))
                    stdin.flush()
                    continue

                raise MethodNotAllowed(
                    valid_methods=['GET', 'PUT'],
                    description='Only GET and PUT methods are allowed for paper muncher',
                )

    @staticmethod
    def _construct_args(*args, **kwargs):
        extra_args = list(args)
        for kwarg_name, kwarg_value in kwargs.items():
            extra_args.extend([f"--{kwarg_name}", str(kwarg_value)])
        return extra_args

    def print(self, *args, **kwargs):
        return self._run('print', *self._construct_args(*args, **kwargs))

    def render(self, *args, **kwargs):
        return self._run('render', *self._construct_args(*args, **kwargs))
