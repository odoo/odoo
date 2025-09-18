"""Embedded Sass Protocol client for Dart Sass.

Provides a high-performance SCSS/Sass compiler using the Sass Embedded
Protocol (protobuf over stdin/stdout). Falls back gracefully when the
``sass --embedded`` binary is unavailable.

See https://github.com/sass/embedded-protocol for the protocol specification.
"""

import contextlib
import logging
import threading
from pathlib import Path
from subprocess import PIPE, Popen

from odoo.tools import misc
from odoo.tools.embedded_sass_pb2 import (
    COMPRESSED,
    EXPANDED,
    INDENTED,
    SCSS,
    InboundMessage,
    OutboundMessage,
)

_logger = logging.getLogger(__name__)


class SassCompileError(Exception):
    """Raised when Sass compilation fails."""


class SassProtocolError(Exception):
    """Raised on embedded protocol violations."""


# ---------------------------------------------------------------------------
# Varint helpers (protobuf wire format)
# ---------------------------------------------------------------------------


def _encode_varint(value: int) -> bytes:
    """Encode an unsigned integer as a protobuf varint."""
    parts = []
    while value > 0x7F:
        parts.append((value & 0x7F) | 0x80)
        value >>= 7
    parts.append(value & 0x7F)
    return bytes(parts)


def _read_varint(stream) -> int | None:
    """Read an unsigned varint from a binary stream. Returns None on EOF."""
    result = 0
    shift = 0
    while True:
        byte = stream.read(1)
        if not byte:
            return None
        b = byte[0]
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result
        shift += 7
        if shift >= 64:
            raise SassProtocolError("Varint too long")


# ---------------------------------------------------------------------------
# Sass Importer interface
# ---------------------------------------------------------------------------


class SassImporter:
    """Base class for custom Sass importers."""

    def canonicalize(self, url: str, from_import: bool) -> str | None:
        """Return a canonical URL for the given import, or None."""
        raise NotImplementedError

    def load(self, canonical_url: str) -> tuple[str, str] | None:
        """Return (contents, syntax) for a canonical URL, or None."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Embedded Sass Compiler
# ---------------------------------------------------------------------------


class SassEmbeddedCompiler:
    """Client for the Sass Embedded Protocol.

    Manages a long-running ``sass --embedded`` subprocess and communicates
    via protobuf-encoded messages over stdin/stdout.

    Usage::

        compiler = SassEmbeddedCompiler()
        css = compiler.compile_string(
            ".a { .b { color: red; } }",
            style="compressed",
        )
        compiler.close()

    Or as a context manager::

        with SassEmbeddedCompiler() as compiler:
            css = compiler.compile_string(source)
    """

    _unavailable: bool = False  # class-level: skip retrying after first failure

    def __init__(self, sass_path: str | None = None):
        self._sass_path = sass_path
        self._process: Popen | None = None
        self._lock = threading.Lock()
        self._compilation_id = 0
        self._started = False

    def _start(self):
        """Spawn the ``sass --embedded`` subprocess."""
        if self._started:
            return
        if SassEmbeddedCompiler._unavailable:
            raise SassProtocolError("sass --embedded is unavailable")

        sass_path = self._sass_path
        if sass_path is None:
            try:
                sass_path = misc.find_in_path("sass")
            except OSError:
                sass_path = "sass"

        try:
            self._process = Popen(
                [sass_path, "--embedded"],
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE,
            )
        except OSError as e:
            SassEmbeddedCompiler._unavailable = True
            raise SassProtocolError(f"Could not start sass --embedded: {e}") from e

        # Verify the process started successfully
        if self._process.poll() is not None:
            proc = self._process
            self._process = None
            stderr = proc.stderr.read().decode(errors="replace")
            for pipe in (proc.stdin, proc.stdout, proc.stderr):
                with contextlib.suppress(OSError):
                    pipe.close()
            proc.wait()  # reap the zombie
            SassEmbeddedCompiler._unavailable = True
            raise SassProtocolError(f"sass --embedded exited immediately: {stderr}")
        self._started = True

    def _send_packet(self, compilation_id: int, message_bytes: bytes):
        """Send a varint-framed packet to the compiler."""
        cid_bytes = _encode_varint(compilation_id)
        payload = cid_bytes + message_bytes
        length_bytes = _encode_varint(len(payload))
        self._process.stdin.write(length_bytes + payload)
        self._process.stdin.flush()

    def _recv_packet(self) -> tuple[int, bytes]:
        """Read a varint-framed packet from the compiler.

        Returns (compilation_id, protobuf_bytes).
        """
        length = _read_varint(self._process.stdout)
        if length is None:
            raise SassProtocolError("Unexpected EOF from sass --embedded")

        # Read the full payload
        payload = self._process.stdout.read(length)
        if len(payload) != length:
            raise SassProtocolError(
                f"Short read: expected {length} bytes, got {len(payload)}"
            )

        # Parse compilation_id from the beginning of payload
        idx = 0
        compilation_id = 0
        shift = 0
        while idx < len(payload):
            b = payload[idx]
            idx += 1
            compilation_id |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7

        return compilation_id, payload[idx:]

    def close(self):
        """Shut down the compiler subprocess."""
        if self._process is not None:
            proc = self._process
            self._process = None
            self._started = False
            for pipe in (proc.stdin, proc.stdout, proc.stderr):
                with contextlib.suppress(OSError):
                    pipe.close()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
                proc.wait()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def compile_string(
        self,
        source: str,
        *,
        syntax: str = "scss",
        style: str = "expanded",
        source_map: bool = False,
        importers: list[SassImporter] | None = None,
        load_paths: list[str] | None = None,
        quiet_deps: bool = True,
        url: str = "",
    ) -> str:
        """Compile a Sass/SCSS string to CSS.

        Args:
            source: The stylesheet source code.
            syntax: One of 'scss', 'indented', 'css'.
            style: One of 'expanded', 'compressed'.
            source_map: Whether to generate a source map.
            importers: Custom importers for resolving ``@import``/``@use``.
            load_paths: Filesystem paths to search for imports.
            quiet_deps: Suppress deprecation warnings from dependencies.
            url: The URL of the source file (for error messages).

        Returns:
            The compiled CSS string.

        Raises:
            SassCompileError: If compilation fails.
            SassProtocolError: If a protocol error occurs.
        """
        with self._lock:
            self._start()
            self._compilation_id += 1
            compilation_id = self._compilation_id

            try:
                return self._do_compile(
                    compilation_id,
                    source,
                    syntax,
                    style,
                    source_map,
                    importers or [],
                    load_paths or [],
                    quiet_deps,
                    url,
                )
            except SassCompileError:
                raise
            except Exception:
                # Process crashed during communication — mark unavailable
                # and close to reap the zombie process.
                SassEmbeddedCompiler._unavailable = True
                self.close()
                raise

    def _do_compile(
        self,
        compilation_id: int,
        source: str,
        syntax: str,
        style: str,
        source_map: bool,
        importers: list[SassImporter],
        load_paths: list[str],
        quiet_deps: bool,
        url: str,
    ) -> str:
        """Execute a single compilation request/response cycle."""
        # Build the CompileRequest
        syntax_enum = {"scss": SCSS, "indented": INDENTED, "css": 2}.get(syntax, SCSS)
        style_enum = COMPRESSED if style == "compressed" else EXPANDED

        request = InboundMessage()
        compile_req = request.compile_request
        compile_req.id = compilation_id

        # StringInput
        string_input = compile_req.string
        string_input.source = source
        string_input.syntax = syntax_enum
        if url:
            string_input.url = url

        compile_req.style = style_enum
        compile_req.source_map = source_map
        compile_req.quiet_deps = quiet_deps

        # Build importer list: custom importers first, then load paths
        importer_id_map = {}
        for i, imp in enumerate(importers):
            importer_msg = compile_req.importers.add()
            importer_id = i + 1  # IDs start at 1
            importer_msg.importer_id = importer_id
            importer_id_map[importer_id] = imp

        for path in load_paths:
            importer_msg = compile_req.importers.add()
            importer_msg.path = path

        # Serialize and send
        msg_bytes = request.SerializeToString()
        self._send_packet(compilation_id, msg_bytes)

        # Process responses until we get a CompileResponse
        while True:
            recv_cid, recv_bytes = self._recv_packet()
            outbound = OutboundMessage()
            outbound.ParseFromString(recv_bytes)

            msg_type = outbound.WhichOneof("message")

            if msg_type == "compile_response":
                resp = outbound.compile_response
                result_type = resp.WhichOneof("result")
                if result_type == "success":
                    return resp.success.css
                elif result_type == "failure":
                    raise SassCompileError(
                        resp.failure.formatted or resp.failure.message
                    )
                else:
                    raise SassProtocolError("CompileResponse has no result")

            elif msg_type == "log_event":
                event = outbound.log_event
                if event.type == 2:  # DEBUG
                    _logger.debug("Sass debug: %s", event.message)
                else:
                    # WARNING or DEPRECATION_WARNING — log at debug level
                    # since we use quiet_deps to suppress most noise
                    _logger.debug("Sass warning: %s", event.formatted or event.message)

            elif msg_type == "canonicalize_request":
                req = outbound.canonicalize_request
                importer = importer_id_map.get(req.importer_id)
                response = InboundMessage()
                canon_resp = response.canonicalize_response
                canon_resp.id = req.id
                if importer is not None:
                    try:
                        result = importer.canonicalize(req.url, req.from_import)
                        if result is not None:
                            canon_resp.url = result
                    except Exception as e:
                        canon_resp.error = str(e)
                self._send_packet(recv_cid, response.SerializeToString())

            elif msg_type == "import_request":
                req = outbound.import_request
                importer = importer_id_map.get(req.importer_id)
                response = InboundMessage()
                import_resp = response.import_response
                import_resp.id = req.id
                if importer is not None:
                    try:
                        result = importer.load(req.url)
                        if result is not None:
                            contents, file_syntax = result
                            success = import_resp.success
                            success.contents = contents
                            syntax_val = {
                                "scss": SCSS,
                                "indented": INDENTED,
                                "css": 2,
                            }.get(file_syntax, SCSS)
                            success.syntax = syntax_val
                            success.source_map_url = req.url
                    except Exception as e:
                        import_resp.error = str(e)
                self._send_packet(recv_cid, response.SerializeToString())

            elif msg_type == "error":
                proto_err = outbound.error
                raise SassProtocolError(
                    f"Protocol error ({proto_err.type}): {proto_err.message}"
                )

            else:
                _logger.debug("Ignoring unhandled message type: %s", msg_type)


# ---------------------------------------------------------------------------
# Odoo-specific importer
# ---------------------------------------------------------------------------


def _resolve_sass_path(base: str) -> list[str]:
    """Generate candidate paths for Sass partial resolution.

    Given a base path like ``/path/to/foo``, returns candidates in order:
    - /path/to/foo.scss
    - /path/to/foo.sass
    - /path/to/_foo.scss
    - /path/to/_foo.sass
    - /path/to/foo/index.scss
    - /path/to/foo/index.sass
    - /path/to/foo/_index.scss
    - /path/to/foo/_index.sass
    """
    base_path = Path(base)
    dirname = base_path.parent
    basename = base_path.name
    candidates = []

    # If already has an extension, try as-is and with underscore prefix
    if base_path.suffix in (".scss", ".sass", ".css"):
        candidates.extend((base, str(dirname / f"_{basename}")))
        return candidates

    # Try with extensions
    candidates.extend(base + ext for ext in (".scss", ".sass"))
    candidates.extend(str(dirname / f"_{basename}{ext}") for ext in (".scss", ".sass"))

    # Try index files
    candidates.extend(str(base_path / f"index{ext}") for ext in (".scss", ".sass"))
    candidates.extend(str(base_path / f"_index{ext}") for ext in (".scss", ".sass"))

    return candidates


class OdooSassImporter(SassImporter):
    """Sass importer that resolves imports using Odoo's addon paths.

    Mirrors the behavior of the existing ``scss_importer`` closure in
    ``ScssStylesheetAsset.compile()`` but adapted for the Embedded Sass
    Protocol's canonicalize/load two-step interface.
    """

    def __init__(self, bootstrap_path: str):
        self.bootstrap_path = bootstrap_path

    def canonicalize(self, url: str, from_import: bool) -> str | None:
        """Resolve an import URL to a canonical file:// URL."""
        from odoo.tools.misc import file_path

        *parent_parts, filename = url.replace("\\", "/").split("/")
        parent_path_str = str(Path(*parent_parts)) if parent_parts else ""

        # Try resolving via Odoo's file_path first, then bootstrap
        search_dirs = []
        if parent_path_str:
            with contextlib.suppress(FileNotFoundError):
                search_dirs.append(file_path(parent_path_str))
        with contextlib.suppress(FileNotFoundError):
            search_dirs.append(
                file_path(str(Path(self.bootstrap_path) / parent_path_str))
                if parent_path_str
                else self.bootstrap_path
            )

        for search_dir in search_dirs:
            base = str(Path(search_dir) / filename)
            for candidate in _resolve_sass_path(base):
                candidate_path = Path(candidate)
                if candidate_path.is_file():
                    return f"file://{candidate_path.resolve()}"

        return None

    def load(self, canonical_url: str) -> tuple[str, str] | None:
        """Load a stylesheet from a canonical file:// URL."""
        file = Path(canonical_url.removeprefix("file://"))
        if not file.is_file():
            return None
        contents = file.read_text(encoding="utf-8")
        syntax = "indented" if file.suffix == ".sass" else "scss"
        return contents, syntax


# ---------------------------------------------------------------------------
# Singleton management
# ---------------------------------------------------------------------------

_sass_compiler: SassEmbeddedCompiler | None = None
_sass_lock = threading.Lock()


def get_sass_compiler() -> SassEmbeddedCompiler:
    """Return the singleton SassEmbeddedCompiler, creating it lazily."""
    global _sass_compiler
    if _sass_compiler is None:
        with _sass_lock:
            if _sass_compiler is None:
                _sass_compiler = SassEmbeddedCompiler()
    return _sass_compiler


def close_sass_compiler():
    """Shut down the singleton SassEmbeddedCompiler if running."""
    global _sass_compiler
    with _sass_lock:
        if _sass_compiler is not None:
            _sass_compiler.close()
            _sass_compiler = None
