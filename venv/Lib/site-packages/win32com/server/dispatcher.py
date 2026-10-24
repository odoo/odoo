"""Dispatcher

Please see policy.py for a discussion on dispatchers and policies
"""

from __future__ import annotations

import traceback
from typing import NoReturn

import pythoncom
import win32api
import win32com
from win32com.server.exception import IsCOMServerException
from win32com.util import IIDToInterfaceName


class DispatcherBase:
    """The base class for all Dispatchers.

    This dispatcher supports wrapping all operations in exception handlers,
    and all the necessary delegation to the policy.

    This base class supports the printing of "unexpected" exceptions.  Note, however,
    that exactly where the output of print goes may not be useful!  A derived class may
    provide additional semantics for this.
    """

    def __init__(self, policyClass, object):
        self.policy = policyClass(object)
        # The logger we should dump to.  If None, we should send to the
        # default location (typically 'print')
        self.logger = getattr(win32com, "logger", None)

    def _CreateInstance_(self, clsid, reqIID):
        try:
            self.policy._CreateInstance_(clsid, reqIID)
            return pythoncom.WrapObject(self, reqIID)
        except:
            self._HandleException_()

    def _QueryInterface_(self, iid):
        try:
            return self.policy._QueryInterface_(iid)
        except:
            self._HandleException_()

    def _Invoke_(self, dispid, lcid, wFlags, args):
        try:
            return self.policy._Invoke_(dispid, lcid, wFlags, args)
        except:
            self._HandleException_()

    def _GetIDsOfNames_(self, names, lcid):
        try:
            return self.policy._GetIDsOfNames_(names, lcid)
        except:
            self._HandleException_()

    def _GetTypeInfo_(self, index, lcid):
        try:
            return self.policy._GetTypeInfo_(index, lcid)
        except:
            self._HandleException_()

    def _GetTypeInfoCount_(self):
        try:
            return self.policy._GetTypeInfoCount_()
        except:
            self._HandleException_()

    def _GetDispID_(self, name, fdex):
        try:
            return self.policy._GetDispID_(name, fdex)
        except:
            self._HandleException_()

    def _InvokeEx_(self, dispid, lcid, wFlags, args, kwargs, serviceProvider):
        try:
            return self.policy._InvokeEx_(
                dispid, lcid, wFlags, args, kwargs, serviceProvider
            )
        except:
            self._HandleException_()

    def _DeleteMemberByName_(self, name, fdex):
        try:
            return self.policy._DeleteMemberByName_(name, fdex)
        except:
            self._HandleException_()

    def _DeleteMemberByDispID_(self, id):
        try:
            return self.policy._DeleteMemberByDispID_(id)
        except:
            self._HandleException_()

    def _GetMemberProperties_(self, id, fdex):
        try:
            return self.policy._GetMemberProperties_(id, fdex)
        except:
            self._HandleException_()

    def _GetMemberName_(self, dispid):
        try:
            return self.policy._GetMemberName_(dispid)
        except:
            self._HandleException_()

    def _GetNextDispID_(self, fdex, flags):
        try:
            return self.policy._GetNextDispID_(fdex, flags)
        except:
            self._HandleException_()

    def _GetNameSpaceParent_(self):
        try:
            return self.policy._GetNameSpaceParent_()
        except:
            self._HandleException_()

    def _HandleException_(self) -> NoReturn:
        """Called whenever an exception is raised.

        Default behaviour is to print the exception.
        """
        # If not a COM exception, print it for the developer.
        if not IsCOMServerException():
            if self.logger is not None:
                self.logger.exception("pythoncom server error")
            else:
                traceback.print_exc()
        # But still raise it for the framework.
        raise

    def _trace_(self, *args):
        if self.logger is not None:
            record = " ".join(map(str, args))
            self.logger.debug(record)
        else:
            for arg in args[:-1]:
                print(arg, end=" ")
            print(args[-1])


class DispatcherTrace(DispatcherBase):
    """A dispatcher, which causes a 'print' line for each COM function called."""

    def _QueryInterface_(self, iid):
        rc = DispatcherBase._QueryInterface_(self, iid)
        if not rc:
            self._trace_(
                "in {!r}._QueryInterface_ with unsupported IID {} ({})".format(
                    self.policy._obj_, IIDToInterfaceName(iid), iid
                )
            )
        return rc

    def _GetIDsOfNames_(self, names, lcid):
        self._trace_("in _GetIDsOfNames_ with '%s' and '%d'\n" % (names, lcid))
        return DispatcherBase._GetIDsOfNames_(self, names, lcid)

    def _GetTypeInfo_(self, index, lcid):
        self._trace_("in _GetTypeInfo_ with index=%d, lcid=%d\n" % (index, lcid))
        return DispatcherBase._GetTypeInfo_(self, index, lcid)

    def _GetTypeInfoCount_(self):
        self._trace_("in _GetTypeInfoCount_\n")
        return DispatcherBase._GetTypeInfoCount_(self)

    def _Invoke_(self, dispid, lcid, wFlags, args):
        self._trace_("in _Invoke_ with", dispid, lcid, wFlags, args)
        return DispatcherBase._Invoke_(self, dispid, lcid, wFlags, args)

    def _GetDispID_(self, name, fdex):
        self._trace_("in _GetDispID_ with", name, fdex)
        return DispatcherBase._GetDispID_(self, name, fdex)

    def _InvokeEx_(self, dispid, lcid, wFlags, args, kwargs, serviceProvider):
        self._trace_(
            "in {!r}._InvokeEx_-{}{!r} [{:x},{},{!r}]".format(
                self.policy._obj_, dispid, args, wFlags, lcid, serviceProvider
            )
        )
        return DispatcherBase._InvokeEx_(
            self, dispid, lcid, wFlags, args, kwargs, serviceProvider
        )

    def _DeleteMemberByName_(self, name, fdex):
        self._trace_("in _DeleteMemberByName_ with", name, fdex)
        return DispatcherBase._DeleteMemberByName_(self, name, fdex)

    def _DeleteMemberByDispID_(self, id):
        self._trace_("in _DeleteMemberByDispID_ with", id)
        return DispatcherBase._DeleteMemberByDispID_(self, id)

    def _GetMemberProperties_(self, id, fdex):
        self._trace_("in _GetMemberProperties_ with", id, fdex)
        return DispatcherBase._GetMemberProperties_(self, id, fdex)

    def _GetMemberName_(self, dispid):
        self._trace_("in _GetMemberName_ with", dispid)
        return DispatcherBase._GetMemberName_(self, dispid)

    def _GetNextDispID_(self, fdex, flags):
        self._trace_("in _GetNextDispID_ with", fdex, flags)
        return DispatcherBase._GetNextDispID_(self, fdex, flags)

    def _GetNameSpaceParent_(self):
        self._trace_("in _GetNameSpaceParent_")
        return DispatcherBase._GetNameSpaceParent_(self)


class DispatcherWin32trace(DispatcherTrace):
    """A tracing dispatcher that sends its output to the win32trace remote collector."""

    def __init__(self, policyClass, object):
        DispatcherTrace.__init__(self, policyClass, object)
        if self.logger is None:
            # If we have no logger, setup our output.
            import win32traceutil  # Sets up everything.
        self._trace_(f"Object with win32trace dispatcher created (object={object!r})")


class DispatcherOutputDebugString(DispatcherTrace):
    """A tracing dispatcher that sends its output to win32api.OutputDebugString"""

    def _trace_(self, *args):
        for arg in args[:-1]:
            win32api.OutputDebugString(str(arg) + " ")
        win32api.OutputDebugString(str(args[-1]) + "\n")


try:
    import win32trace  # nopycln: import # Check for win32traceutil w/o importing it

    DefaultDebugDispatcher: type[DispatcherTrace] = DispatcherWin32trace
except ImportError:  # no win32trace module - just use a print based one.
    DefaultDebugDispatcher = DispatcherTrace
