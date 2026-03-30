from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
import errno
import fcntl
import json
import os
import pty
import signal
import struct
import termios
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config import get_settings
from .token import validate_terminal_token


router = APIRouter()

INVALID_TOKEN_CLOSE_CODE = 4001
DEFAULT_TERMINAL_COLS = 120
DEFAULT_TERMINAL_ROWS = 32


def _set_pty_size(fd: int, cols: int, rows: int) -> None:
    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)


def _build_preexec(slave_fd: int):
    def _preexec() -> None:
        os.setsid()
        fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)

    return _preexec


async def _read_pty(master_fd: int) -> bytes:
    return await asyncio.to_thread(os.read, master_fd, 4096)


@dataclass
class RunningCommand:
    process: asyncio.subprocess.Process
    master_fd: int
    output_task: asyncio.Task[None]
    wait_task: asyncio.Task[None]


class TerminalConnection:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.settings = get_settings()
        self.send_lock = asyncio.Lock()
        self.cols = DEFAULT_TERMINAL_COLS
        self.rows = DEFAULT_TERMINAL_ROWS
        self.running: RunningCommand | None = None

    async def send_json(self, payload: dict[str, Any]) -> None:
        async with self.send_lock:
            await self.websocket.send_json(payload)

    async def start_command(self, command: str) -> None:
        if self.running and self.running.process.returncode is None:
            await self.send_json({"type": "error", "data": "Process already running"})
            return

        self.settings.output_path.mkdir(parents=True, exist_ok=True)
        master_fd, slave_fd = pty.openpty()
        _set_pty_size(master_fd, self.cols, self.rows)
        _set_pty_size(slave_fd, self.cols, self.rows)

        env = os.environ.copy()
        env["KODOO_ENGINE_URL"] = "http://localhost:8765"

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(self.settings.output_path),
                env=env,
                executable="/bin/bash",
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                preexec_fn=_build_preexec(slave_fd),
            )
        finally:
            os.close(slave_fd)

        output_task = asyncio.create_task(self._stream_output(master_fd))
        wait_task = asyncio.create_task(self._wait_for_exit(process, master_fd, output_task))
        self.running = RunningCommand(
            process=process,
            master_fd=master_fd,
            output_task=output_task,
            wait_task=wait_task,
        )

    async def interrupt(self) -> None:
        if not self.running or self.running.process.returncode is not None:
            await self.send_json({"type": "error", "data": "No running process"})
            return
        try:
            os.killpg(os.getpgid(self.running.process.pid), signal.SIGINT)
        except ProcessLookupError:
            pass

    async def resize(self, cols: int | None, rows: int | None) -> None:
        if cols:
            self.cols = max(2, int(cols))
        if rows:
            self.rows = max(1, int(rows))
        if self.running:
            _set_pty_size(self.running.master_fd, self.cols, self.rows)
            if self.running.process.returncode is None:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(os.getpgid(self.running.process.pid), signal.SIGWINCH)

    async def shutdown(self) -> None:
        if not self.running:
            return
        process = self.running.process
        wait_task = self.running.wait_task
        output_task = self.running.output_task
        master_fd = self.running.master_fd
        self.running = None

        if process.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(process.wait(), timeout=3)
            if process.returncode is None:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)

        for task in (output_task, wait_task):
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        with contextlib.suppress(OSError):
            os.close(master_fd)

    async def _stream_output(self, master_fd: int) -> None:
        try:
            while True:
                try:
                    chunk = await _read_pty(master_fd)
                except OSError as exc:
                    if exc.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                await self.send_json(
                    {
                        "type": "output",
                        "data": chunk.decode("utf-8", errors="replace"),
                    }
                )
        except (RuntimeError, WebSocketDisconnect):
            pass
        finally:
            with contextlib.suppress(OSError):
                os.close(master_fd)

    async def _wait_for_exit(
        self,
        process: asyncio.subprocess.Process,
        master_fd: int,
        output_task: asyncio.Task[None],
    ) -> None:
        try:
            return_code = await process.wait()
            with contextlib.suppress(asyncio.CancelledError):
                await output_task
            await self.send_json({"type": "exit", "code": return_code})
        except (RuntimeError, WebSocketDisconnect):
            pass
        finally:
            if self.running and self.running.process is process:
                self.running = None
            with contextlib.suppress(OSError):
                os.close(master_fd)


@router.websocket("/ws/terminal")
async def terminal_socket(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    valid, _uid = validate_terminal_token(get_settings().terminal_secret, token)
    if not valid:
        await websocket.accept()
        await websocket.close(code=INVALID_TOKEN_CLOSE_CODE)
        return

    await websocket.accept()
    connection = TerminalConnection(websocket)
    await connection.send_json(
        {
            "type": "ready",
            "cwd": str(connection.settings.output_path),
        }
    )

    try:
        while True:
            raw_message = await websocket.receive_text()
            try:
                payload = json.loads(raw_message)
            except json.JSONDecodeError:
                await connection.send_json({"type": "error", "data": "Invalid JSON message"})
                continue

            message_type = payload.get("type")
            if message_type == "input":
                command = str(payload.get("data", "")).strip()
                if not command:
                    await connection.send_json({"type": "error", "data": "Command is empty"})
                    continue
                await connection.start_command(command)
                continue

            if message_type == "signal":
                if payload.get("data") != "SIGINT":
                    await connection.send_json({"type": "error", "data": "Unsupported signal"})
                    continue
                await connection.interrupt()
                continue

            if message_type == "resize":
                await connection.resize(payload.get("cols"), payload.get("rows"))
                continue

            await connection.send_json({"type": "error", "data": "Unsupported message type"})
    except WebSocketDisconnect:
        pass
    finally:
        await connection.shutdown()
