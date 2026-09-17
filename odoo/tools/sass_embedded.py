import atexit
import collections
import contextlib
import logging
import re
import shutil
import subprocess
import threading
from pathlib import Path
from subprocess import PIPE, Popen
from typing import IO, Self

from google.protobuf.message import DecodeError

import odoo
from odoo.libs._vendor.embedded_sass_pb2 import (  # type: ignore[attr-defined]
    COMPRESSED,
    CSS,
    EXPANDED,
    INDENTED,
    SCSS,
    InboundMessage,
    OutboundMessage,
)
from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_RX_DEPRECATION = re.compile(r"DEPRECATION WARNING \[([a-z-]+)\]")
_RX_OMITTED = re.compile(r"(\d+) repetitive deprecation warnings omitted")
_SYNTAX_ENUM = {"scss": SCSS, "indented": INDENTED, "css": CSS}

_COMPILE_TIMEOUT_S = 120.0


def _kill_wedged_sass(proc: Popen) -> None:
    _logger.warning(
        "sass --embedded compile exceeded %ss; killing the wedged process",
        _COMPILE_TIMEOUT_S,
    )
    with contextlib.suppress(Exception):
        proc.kill()


class SassCompileError(Exception):
    pass


class SassProtocolError(Exception):
    pass


class SassNotFoundError(SassProtocolError):
    pass


def _encode_varint(value: int) -> bytes:
    parts = []
    while value > 0x7F:
        parts.append((value & 0x7F) | 0x80)
        value >>= 7
    parts.append(value & 0x7F)
    return bytes(parts)


def _read_varint(stream: IO[bytes]) -> int | None:
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
            msg = "Varint too long"
            raise SassProtocolError(msg)


class SassImporter:
    def canonicalize(self, url: str, from_import: bool) -> str | None:
        raise NotImplementedError

    def load(self, canonical_url: str) -> tuple[str, str] | None:
        raise NotImplementedError


def _supports_embedded(sass_path: str) -> bool:
    try:
        proc = subprocess.run(
            [sass_path, "--embedded"],
            input=b"",
            stdout=PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
            check=False,
        )
    except OSError, subprocess.SubprocessError:
        return False
    if proc.returncode != 0:
        return False
    out = (proc.stdout or b"").lower()
    return b"unavailable" not in out and b"pure js" not in out


def get_sass_path() -> str | None:
    node_modules = Path(odoo.__path__[0]).parent / "node_modules"
    candidates: list[str] = []
    system_sass = shutil.which("sass")
    if system_sass:
        candidates.append(system_sass)
    candidates += sorted(
        str(p) for p in node_modules.glob("sass-embedded-*/dart-sass/sass")
    )
    for candidate in candidates:
        if _supports_embedded(candidate):
            _debug.logic("sass.binary_chosen", path=candidate, probed=len(candidates))
            return candidate
    fallback = shutil.which("sass", path=str(node_modules / ".bin"))
    _debug.logic("sass.binary_fallback", path=fallback, probed=len(candidates))
    return fallback


class SassEmbeddedCompiler:
    def __init__(self, sass_path: str | None = None) -> None:
        self._sass_path = sass_path
        self._process: Popen | None = None
        self._lock = threading.Lock()
        self._compilation_id = 0
        self._started = False

    def _start(self) -> None:
        if self._started and self._process is not None and self._process.poll() is None:
            return
        _debug.logic(
            "sass.process_restart",
            started=self._started,
            exit_code=None if self._process is None else self._process.poll(),
        )
        self.close()

        sass_path = self._sass_path
        if sass_path is None:
            sass_path = get_sass_path()
        if sass_path is None:
            raise SassNotFoundError(
                "Dart Sass not found. It is a required dependency of this fork: "
                "run `npm install` in the Odoo root (declared in package.json) "
                "or install a `sass` binary on PATH."
            )

        try:
            self._process = Popen(
                [sass_path, "--embedded"],
                stdin=PIPE,
                stdout=PIPE,
                stderr=subprocess.DEVNULL,
            )
        except OSError as e:
            raise SassProtocolError(f"Could not start sass --embedded: {e}") from e

        if self._process.poll() is not None:
            returncode = self._process.returncode
            self.close()
            raise SassProtocolError(
                f"sass --embedded exited immediately with code {returncode}"
            )
        self._started = True
        _debug.lifecycle("sass.process_started", pid=self._process.pid, path=sass_path)

    def _pipes(self) -> tuple[IO[bytes], IO[bytes]]:
        proc = self._process
        if proc is None or proc.stdin is None or proc.stdout is None:
            msg = "sass --embedded is not running"
            raise SassProtocolError(msg)
        return proc.stdin, proc.stdout

    def _send_packet(self, compilation_id: int, message_bytes: bytes) -> None:
        stdin, _stdout = self._pipes()
        cid_bytes = _encode_varint(compilation_id)
        payload = cid_bytes + message_bytes
        length_bytes = _encode_varint(len(payload))
        stdin.write(length_bytes + payload)
        stdin.flush()

    def _recv_packet(self) -> tuple[int, bytes]:
        _stdin, stdout = self._pipes()
        length = _read_varint(stdout)
        if length is None:
            msg = "Unexpected EOF from sass --embedded"
            raise SassProtocolError(msg)

        payload = stdout.read(length)
        if len(payload) != length:
            raise SassProtocolError(
                f"Short read: expected {length} bytes, got {len(payload)}"
            )

        idx = 0
        compilation_id = 0
        shift = 0
        terminated = False
        while idx < len(payload):
            b = payload[idx]
            idx += 1
            compilation_id |= (b & 0x7F) << shift
            if not (b & 0x80):
                terminated = True
                break
            shift += 7
            if shift >= 64:
                msg = "Varint too long"
                raise SassProtocolError(msg)
        if not terminated:
            msg = "Truncated compilation id in packet from sass --embedded"
            raise SassProtocolError(msg)

        return compilation_id, payload[idx:]

    def close(self) -> None:
        if self._process is not None:
            proc = self._process
            self._process = None
            self._started = False
            for pipe in (proc.stdin, proc.stdout):
                if pipe is not None:
                    with contextlib.suppress(OSError):
                        pipe.close()
            killed = False  # debuglog
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
                proc.wait()
                killed = True  # debuglog
            _debug.lifecycle(
                "sass.process_closed",
                pid=proc.pid,
                exit_code=proc.returncode,
                killed=killed,
                compilations=self._compilation_id,
            )

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
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
        with self._lock:
            self._start()
            self._compilation_id += 1
            compilation_id = self._compilation_id

            watchdog = threading.Timer(
                _COMPILE_TIMEOUT_S, _kill_wedged_sass, (self._process,)
            )
            watchdog.daemon = True
            watchdog.start()
            try:
                with _debug.perf(
                    "sass.compile",
                    compilation=compilation_id,
                    url=url,
                    syntax=syntax,
                    style=style,
                    source_bytes=len(source),
                    importers=len(importers or ()),
                ):
                    return self._compile_with_embedded_sass(
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
            except SassCompileError as exc:
                _debug.logic(
                    "sass.compile_failed",
                    compilation=compilation_id,
                    url=url,
                    error=type(exc).__name__,
                )
                raise
            except Exception as exc:
                _debug.logic(
                    "sass.protocol_failed",
                    compilation=compilation_id,
                    url=url,
                    error=type(exc).__name__,
                )
                self.close()
                raise
            finally:
                watchdog.cancel()

    def _prepare_compile_request(
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
    ) -> tuple[InboundMessage, dict[int, SassImporter]]:
        request = InboundMessage()
        compile_req = request.compile_request
        compile_req.id = compilation_id

        string_input = compile_req.string
        string_input.source = source
        string_input.syntax = _SYNTAX_ENUM.get(syntax, SCSS)
        if url:
            string_input.url = url

        compile_req.style = COMPRESSED if style == "compressed" else EXPANDED
        compile_req.source_map = source_map
        compile_req.quiet_deps = quiet_deps

        importer_id_map = {}
        for i, imp in enumerate(importers):
            importer_msg = compile_req.importers.add()
            importer_msg.importer_id = i + 1
            importer_id_map[i + 1] = imp

        for path in load_paths:
            compile_req.importers.add().path = path

        return request, importer_id_map

    @staticmethod
    def _compile_response_css(
        resp, url: str, deprecations: collections.Counter[str]
    ) -> str:
        result_type = resp.WhichOneof("result")
        if result_type == "failure":
            raise SassCompileError(resp.failure.formatted or resp.failure.message)
        if result_type != "success":
            msg = "CompileResponse has no result"
            raise SassProtocolError(msg)
        if deprecations:
            _logger.info(
                "Sass compiled %s with %s deprecation warning(s): %s",
                url or "<string>",
                sum(deprecations.values()),
                ", ".join(
                    f"{name}={count}" for name, count in deprecations.most_common()
                ),
            )
        _debug.perf.count(
            "sass.compiled",
            url=url or "<string>",
            css_bytes=len(resp.success.css),
            deprecations=sum(deprecations.values()),
            loaded_urls=len(resp.success.loaded_urls),
        )
        return resp.success.css

    @staticmethod
    def _record_log_event(event, deprecations: collections.Counter[str]) -> None:
        if event.type == 2:
            _logger.debug("Sass debug: %s", event.message)
            return
        text = event.formatted or event.message
        _logger.debug("Sass warning: %s", text)
        if category := _RX_DEPRECATION.search(text):
            deprecations[category.group(1)] += 1
        elif omitted := _RX_OMITTED.search(text):
            deprecations["(repeats omitted by sass)"] += int(omitted.group(1))

    @staticmethod
    def _canonicalize_response(req, importer: SassImporter | None) -> InboundMessage:
        response = InboundMessage()
        canon_resp = response.canonicalize_response
        canon_resp.id = req.id
        if importer is not None:
            try:
                canonical_url = importer.canonicalize(req.url, req.from_import)
                if canonical_url is not None:
                    canon_resp.url = canonical_url
                _debug.logic(
                    "sass.canonicalize",
                    url=req.url,
                    from_import=req.from_import,
                    resolved=canonical_url,
                )
            except Exception as e:
                canon_resp.error = str(e)
                _debug.logic(
                    "sass.canonicalize_failed", url=req.url, error=type(e).__name__
                )
        return response

    @staticmethod
    def _import_response(req, importer: SassImporter | None) -> InboundMessage:
        response = InboundMessage()
        import_resp = response.import_response
        import_resp.id = req.id
        if importer is not None:
            try:
                loaded = importer.load(req.url)
                if loaded is not None:
                    contents, file_syntax = loaded
                    success = import_resp.success
                    success.contents = contents
                    success.syntax = _SYNTAX_ENUM.get(file_syntax, SCSS)
                    success.source_map_url = req.url
                _debug.logic(
                    "sass.import",
                    url=req.url,
                    found=loaded is not None,
                    size=None if loaded is None else len(loaded[0]),
                )
            except Exception as e:
                import_resp.error = str(e)
                _debug.logic("sass.import_failed", url=req.url, error=type(e).__name__)
        return response

    def _compile_with_embedded_sass(
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
        deprecations: collections.Counter[str] = collections.Counter()
        request, importer_id_map = self._prepare_compile_request(
            compilation_id,
            source,
            syntax,
            style,
            source_map,
            importers,
            load_paths,
            quiet_deps,
            url,
        )
        self._send_packet(compilation_id, request.SerializeToString())

        while True:
            recv_cid, recv_bytes = self._recv_packet()
            outbound = OutboundMessage()
            try:
                outbound.ParseFromString(recv_bytes)
            except DecodeError as exc:
                # a framed packet that is not a protobuf message is the
                # transport lying, not the stylesheet; name it as such
                raise SassProtocolError(
                    f"sass --embedded sent an undecodable packet: {exc}"
                ) from exc
            msg_type = outbound.WhichOneof("message")

            if recv_cid != compilation_id and msg_type != "error":
                _debug.logic(
                    "sass.desynchronized",
                    sent=compilation_id,
                    received=recv_cid,
                    message=msg_type,
                )
                raise SassProtocolError(
                    f"sass --embedded desynchronized: sent compilation id "
                    f"{compilation_id}, received {recv_cid} ({msg_type})"
                )

            match msg_type:
                case "compile_response":
                    return self._compile_response_css(
                        outbound.compile_response, url, deprecations
                    )
                case "log_event":
                    self._record_log_event(outbound.log_event, deprecations)
                case "canonicalize_request":
                    req = outbound.canonicalize_request
                    self._send_packet(
                        recv_cid,
                        self._canonicalize_response(
                            req, importer_id_map.get(req.importer_id)
                        ).SerializeToString(),
                    )
                case "import_request":
                    req = outbound.import_request
                    self._send_packet(
                        recv_cid,
                        self._import_response(
                            req, importer_id_map.get(req.importer_id)
                        ).SerializeToString(),
                    )
                case "error":
                    proto_err = outbound.error
                    raise SassProtocolError(
                        f"Protocol error ({proto_err.type}): {proto_err.message}"
                    )
                case _:
                    _logger.debug("Ignoring unhandled message type: %s", msg_type)


def _get_sass_path_candidates(base: str) -> list[str]:
    base_path = Path(base)
    dirname = base_path.parent
    basename = base_path.name
    candidates: list[str] = []

    if base_path.suffix in (".scss", ".sass", ".css"):
        candidates.extend((base, str(dirname / f"_{basename}")))
        return candidates

    candidates.extend(base + ext for ext in (".scss", ".sass"))
    candidates.extend(str(dirname / f"_{basename}{ext}") for ext in (".scss", ".sass"))

    candidates.extend(str(base_path / f"index{ext}") for ext in (".scss", ".sass"))
    candidates.extend(str(base_path / f"_index{ext}") for ext in (".scss", ".sass"))

    return candidates


class OdooSassImporter(SassImporter):
    def __init__(self, bootstrap_path: str) -> None:
        self.bootstrap_path = bootstrap_path

    def canonicalize(self, url: str, from_import: bool) -> str | None:
        from odoo.tools.files import file_path

        *parent_parts, filename = url.replace("\\", "/").split("/")
        parent_path_str = str(Path(*parent_parts)) if parent_parts else ""

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
            for candidate in _get_sass_path_candidates(base):
                candidate_path = Path(candidate)
                if candidate_path.is_file():
                    return f"file://{candidate_path.resolve()}"

        return None

    def load(self, canonical_url: str) -> tuple[str, str] | None:
        file = Path(canonical_url.removeprefix("file://"))
        if not file.is_file():
            return None
        contents = file.read_text(encoding="utf-8")
        syntax = "indented" if file.suffix == ".sass" else "scss"
        return contents, syntax


_sass_compiler: SassEmbeddedCompiler | None = None
_sass_lock = threading.Lock()
_on_stop_registered = False


def get_sass_compiler() -> SassEmbeddedCompiler:
    global _sass_compiler, _on_stop_registered  # noqa: PLW0603  the dart-sass subprocess is a process singleton
    if _sass_compiler is None:
        with _sass_lock:
            if _sass_compiler is None:
                _sass_compiler = SassEmbeddedCompiler()
                atexit.register(close_sass_compiler)
                _debug.lifecycle("sass.compiler_created")
                if not _on_stop_registered:
                    try:
                        from odoo.service.server import CommonServer

                        CommonServer.register_on_stop_hook(close_sass_compiler)
                        _on_stop_registered = True
                    except Exception:
                        _logger.debug(
                            "Could not register sass close on server stop",
                            exc_info=True,
                        )
    return _sass_compiler


def close_sass_compiler() -> None:
    global _sass_compiler  # noqa: PLW0603  the dart-sass subprocess is a process singleton
    with _sass_lock:
        if _sass_compiler is not None:
            _sass_compiler.close()
            _sass_compiler = None
            _debug.lifecycle("sass.compiler_closed")
