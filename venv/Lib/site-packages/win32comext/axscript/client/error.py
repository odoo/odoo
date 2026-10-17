"""Exception and error handling.

This contains the core exceptions that the implementations should raise
as well as the IActiveScriptError interface code.
"""

from __future__ import annotations

import re
import traceback
import warnings
from types import TracebackType
from typing import TYPE_CHECKING

import pythoncom
import win32com.server.util
import winerror
from win32com.axscript import axscript
from win32com.server.exception import COMException

if TYPE_CHECKING:
    from win32comext.axscript.client.debug import DebugManager
    from win32comext.axscript.client.framework import AXScriptCodeBlock, COMScript
    from win32comext.axscript.server.axsite import AXSite

debugging = 0


def FormatForAX(text: str):
    """Format a string suitable for an AX Host"""
    # Replace all " with ', so it works OK in HTML (ie, ASP)
    return ExpandTabs(AddCR(text))


def ExpandTabs(text: str):
    return re.sub(r"\t", "    ", text)


def AddCR(text: str):
    return re.sub(r"\n", "\r\n", text)


class IActiveScriptError:
    """An implementation of IActiveScriptError

    The ActiveX Scripting host calls this client whenever we report
    an exception to it.  This interface provides the exception details
    for the host to report to the user.
    """

    _com_interfaces_ = [axscript.IID_IActiveScriptError]
    _public_methods_ = ["GetSourceLineText", "GetSourcePosition", "GetExceptionInfo"]

    def _query_interface_(self, iid):
        print("IActiveScriptError QI - unknown IID", iid)
        return 0

    def _SetExceptionInfo(self, exc: AXScriptException):
        self.exception = exc

    def GetSourceLineText(self):
        return self.exception.linetext

    def GetSourcePosition(self):
        ctx = self.exception.sourceContext
        # Zero based in the debugger (but our columns are too!)
        return (
            ctx,
            self.exception.lineno + self.exception.startLineNo - 1,
            self.exception.colno,
        )

    def GetExceptionInfo(self):
        return self.exception


class AXScriptException(COMException):
    """A class used as a COM exception.

    Note this has attributes which conform to the standard attributes
    for COM exceptions, plus a few others specific to our IActiveScriptError
    object.
    """

    def __init__(
        self,
        site: COMScript,
        codeBlock: AXScriptCodeBlock | None,
        exc_type: None = None,
        exc_value: BaseException | None = None,
        exc_traceback: None = None,
    ):
        # set properties base class shares via base ctor...
        super().__init__(
            description="Unknown Exception",
            scode=winerror.DISP_E_EXCEPTION,
            source="Python ActiveX Scripting Engine",
        )

        if exc_type is not None or exc_traceback is not None:
            warnings.warn(
                "`exc_type` and `exc_traceback` were redundant and are now unused.",
                category=DeprecationWarning,
                stacklevel=2,
            )

        # And my other values...
        if codeBlock is None:
            self.sourceContext = 0
            self.startLineNo = 0
        else:
            self.sourceContext = codeBlock.sourceContextCookie
            self.startLineNo = codeBlock.startLineNumber
        self.linetext = ""

        self.__BuildFromException(site, exc_value)

    def __BuildFromException(self, site: COMScript, value: BaseException | None):
        if debugging:
            import linecache

            linecache.clearcache()
        try:
            if isinstance(value, SyntaxError):
                self._BuildFromSyntaxError(value)
            else:
                self._BuildFromOther(site, value)
        except:  # Error extracting traceback info!!!
            traceback.print_exc()
            # re-raise.
            raise

    def _BuildFromSyntaxError(self, exc: SyntaxError):
        # Some of these may be None, which upsets us!
        msg = exc.msg or "Unknown Error"
        offset = exc.offset or 0
        line = exc.text or ""
        lineno = exc.lineno or 0

        self.description = FormatForAX(msg)
        self.lineno = lineno
        self.colno = offset - 1
        self.linetext = ExpandTabs(line.rstrip())

    def _BuildFromOther(self, site: COMScript, value: BaseException | None):
        tb = value.__traceback__ if value else None
        exc_type = type(value) if value else None
        self.colno = -1
        self.lineno = 0
        if debugging:  # Full traceback if debugging.
            list = traceback.format_exception(exc_type, value, tb)
            self.description = ExpandTabs("".join(list))
            return
        # Run down the traceback list, looking for the first "<Script..>"
        # Hide traceback above this.  In addition, keep going down
        # looking for a "_*_" attribute, and below hide these also.
        hide_names = [
            "r_import",
            "r_reload",
            "r_open",
        ]  # hide from these functions down in the traceback.
        tb_top = tb
        while tb_top:
            filename, lineno, name, line = self.ExtractTracebackInfo(tb_top, site)
            if filename[:7] == "<Script":
                break
            tb_top = tb_top.tb_next
        format_items = []
        if tb_top:  # found one.
            tb_look: TracebackType | None = tb_top
            # Look down for our bottom
            while tb_look:
                filename, lineno, name, line = self.ExtractTracebackInfo(tb_look, site)
                if name in hide_names:
                    break
                # We can report a line-number, but not a filename.  Therefore,
                # we return the last line-number we find in one of our script
                # blocks.
                if filename.startswith("<Script"):
                    self.lineno = lineno
                    self.linetext = line
                format_items.append((filename, lineno, name, line))
                tb_look = tb_look.tb_next
        else:
            tb_top = tb

        bits = ["Traceback (most recent call last):\n"]
        bits.extend(traceback.format_list(format_items))
        if isinstance(value, pythoncom.com_error):
            desc = f"{value.strerror} (0x{value.hresult:x})"
            if (
                value.hresult == winerror.DISP_E_EXCEPTION
                and value.excepinfo
                and value.excepinfo[2]
            ):
                desc = value.excepinfo[2]
            bits.append("COM Error: " + desc)
        else:
            bits.extend(traceback.format_exception_only(exc_type, value))

        self.description = ExpandTabs("".join(bits))

    def ExtractTracebackInfo(self, tb: TracebackType, site: COMScript):
        import linecache

        lineno = tb.tb_lineno
        co = tb.tb_frame.f_code
        filename = co.co_filename
        name = co.co_name
        line: str | None = linecache.getline(filename, lineno)
        if not line:
            codeBlock = site.scriptCodeBlocks.get(filename)
            if codeBlock:
                # Note: 'line' will now be unicode.
                line = codeBlock.GetLineNo(lineno)
        if line:
            line = line.strip()
        else:
            line = None
        return filename, lineno, name, line


def ProcessAXScriptException(
    scriptingSite: AXSite,
    debugManager: DebugManager,
    exceptionInstance: AXScriptException,
):
    """General function to handle any exception in AX code

    This function creates an instance of our IActiveScriptError interface, and
    gives it to the host, along with out exception class.  The host will
    likely call back on the IActiveScriptError interface to get the source text
    and other information not normally in COM exceptions.
    """
    # traceback.print_exc()
    instance = IActiveScriptError()
    instance._SetExceptionInfo(exceptionInstance)
    gateway = win32com.server.util.wrap(instance, axscript.IID_IActiveScriptError)
    if debugManager:
        fCallOnError = debugManager.HandleRuntimeError()
        if not fCallOnError:
            return None

    try:
        result = scriptingSite.OnScriptError(gateway)
    except pythoncom.com_error as details:
        print("**OnScriptError failed:", details)
        print(f"Exception description: '{exceptionInstance.description!r}'")
        print(f"Exception text: '{exceptionInstance.linetext!r}'")
        result = winerror.S_FALSE

    if result == winerror.S_OK:
        # If the above  returns NOERROR, it is assumed the error has been
        # correctly registered and the value SCRIPT_E_REPORTED is returned.
        ret = COMException(scode=axscript.SCRIPT_E_REPORTED)
        return ret
    else:
        # The error is taken to be unreported and is propagated up the call stack
        # via the IDispatch::Invoke's EXCEPINFO parameter (hr returned is DISP_E_EXCEPTION.
        return exceptionInstance
