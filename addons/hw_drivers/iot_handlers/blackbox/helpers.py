import logging

from dataclasses import dataclass
from typing import Any

_logger = logging.getLogger(__name__)

errors = {
    '000': "No error",
    '001': "PIN accepted.",
    '101': "Fiscal Data Module memory 90% full.",
    '102': "Already handled request.",
    '103': "No record.",
    '199': "Unspecified warning.",
    '201': "No Vat Signing Card or Vat Signing Card broken.",
    '202': "Please initialize the Vat Signing Card with PIN.",
    '203': "Vat Signing Card blocked.",
    '204': "Invalid PIN.",
    '205': "Fiscal Data Module memory full.",
    '206': "Unknown identifier.",
    '207': "Invalid data in message.",
    '208': "Fiscal Data Module not operational.",
    '209': "Fiscal Data Module real time clock corrupt.",
    '210': "Vat Signing Card not compatible with Fiscal Data Module.",
    '299': "Unspecified error.",
}


@dataclass
class FdmStatistics:
    identifier: str
    sequence_number: str
    retry_counter: str
    error1: str
    error2: str
    error3: str
    fdm_unique_manufacturing_number: str
    oldest_recorded_transaction_date: str
    most_recent_recorded_transaction_date: str
    oldest_recorded_error_message_date: str
    most_recent_recorded_error_message_date: str
    total_number_of_dumps_to_port3: str
    real_time_clock_date: str
    real_time_clock_time: str
    manufacturing_number_of_last_connected_cash_system: str
    last_connected_vsc_identification_number: str


@dataclass
class FdmLogMessage:
    identifier: str
    sequence_number: str
    retry_counter: str
    error1: str
    error2: str
    error3: str


class BlackboxError(Exception):
    """Custom exception for Blackbox-related errors."""
    def __init__(self, message: str, details: Any = None):
        super().__init__(message)
        self.details = details


def format_header(id: str, seq: int | str, retry: int | str) -> str:
    seq_str = str(seq).zfill(2)
    retry_str = str(retry).zfill(1)
    return f"{id}{seq_str}{retry_str}"


# Mapping of status labels to emoji used in logs.
_EMOJI_FOR_STATUS: dict[str, str] = {
    "info": "📢",
    "send": "🚀",
    "data": "📥",
    "success": "✅",
    "warning": "⚠️",
    "error": "❌",
    "debug": "🐛",
}

# Mapping of status labels to ANSI colour codes used in logs.
_COLOUR_FOR_STATUS: dict[str, str] = {
    "debug": "\x1b[37m",    # White
    "send": "\x1b[37m",     # White
    "data": "\x1b[37m",     # White
    "success": "\x1b[32m",  # Green
    "warning": "\x1b[33m",  # Yellow
    "error": "\x1b[31m",    # Red
    "info": "\x1b[35m",     # Magenta
}


def log(status: str, usb_port: str, message: str) -> None:
    emoji = _EMOJI_FOR_STATUS.get(status, "")
    color = _COLOUR_FOR_STATUS.get(status, "\x1b[0m")
    prefix = f"{color}{emoji} [{usb_port}] {message} \x1b[0m"
    _logger.info(prefix)


def parse_fdm_statistics(data: str) -> FdmStatistics:
    return FdmStatistics(
        identifier=data[0:1],
        sequence_number=data[1:3],
        retry_counter=data[3:4],
        error1=data[4:5],
        error2=data[5:7],
        error3=data[7:10],
        fdm_unique_manufacturing_number=data[10:21],
        oldest_recorded_transaction_date=data[21:29],
        most_recent_recorded_transaction_date=data[29:37],
        oldest_recorded_error_message_date=data[37:45],
        most_recent_recorded_error_message_date=data[45:53],
        total_number_of_dumps_to_port3=data[53:59],
        real_time_clock_date=data[59:67],
        real_time_clock_time=data[67:73],
        manufacturing_number_of_last_connected_cash_system=data[73:87],
        last_connected_vsc_identification_number=data[87:101],
    )


def parse_fdm_log(data: str):
    if len(data) < 10:
        return

    data = FdmLogMessage(
        identifier=data[0:1],
        sequence_number=data[1:3],
        retry_counter=data[3:4],
        error1=data[4:5],
        error2=data[5:7],
        error3=data[7:10],
    )

    header = format_header(data.identifier, data.sequence_number, data.retry_counter)
    error_message = errors.get(data.error1 + data.error2)
    message = f"Event {header}: {data.error1}{data.error2}-{data.error3}"

    if error_message:
        message += f" - {error_message}"

    log("info", "FDM Message", message)
