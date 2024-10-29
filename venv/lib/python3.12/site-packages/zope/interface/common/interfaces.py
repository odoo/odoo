##############################################################################
#
# Copyright (c) 2003 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Interfaces for standard python exceptions
"""
from zope.interface import Interface
from zope.interface import classImplements


class IException(Interface):
    "Interface for `Exception`"


classImplements(Exception, IException)  # noqa E305


class IStandardError(IException):
    "Interface for `StandardError` (no longer existing.)"


class IWarning(IException):
    "Interface for `Warning`"


classImplements(Warning, IWarning)  # noqa E305


class ISyntaxError(IStandardError):
    "Interface for `SyntaxError`"


classImplements(SyntaxError, ISyntaxError)  # noqa E305


class ILookupError(IStandardError):
    "Interface for `LookupError`"


classImplements(LookupError, ILookupError)  # noqa E305


class IValueError(IStandardError):
    "Interface for `ValueError`"


classImplements(ValueError, IValueError)  # noqa E305


class IRuntimeError(IStandardError):
    "Interface for `RuntimeError`"


classImplements(RuntimeError, IRuntimeError)  # noqa E305


class IArithmeticError(IStandardError):
    "Interface for `ArithmeticError`"


classImplements(ArithmeticError, IArithmeticError)  # noqa E305


class IAssertionError(IStandardError):
    "Interface for `AssertionError`"


classImplements(AssertionError, IAssertionError)  # noqa E305


class IAttributeError(IStandardError):
    "Interface for `AttributeError`"


classImplements(AttributeError, IAttributeError)  # noqa E305


class IDeprecationWarning(IWarning):
    "Interface for `DeprecationWarning`"


classImplements(DeprecationWarning, IDeprecationWarning)  # noqa E305


class IEOFError(IStandardError):
    "Interface for `EOFError`"


classImplements(EOFError, IEOFError)  # noqa E305


class IEnvironmentError(IStandardError):
    "Interface for `EnvironmentError`"


classImplements(EnvironmentError, IEnvironmentError)  # noqa E305


class IFloatingPointError(IArithmeticError):
    "Interface for `FloatingPointError`"


classImplements(FloatingPointError, IFloatingPointError)  # noqa E305


class IIOError(IEnvironmentError):
    "Interface for `IOError`"


classImplements(IOError, IIOError)  # noqa E305


class IImportError(IStandardError):
    "Interface for `ImportError`"


classImplements(ImportError, IImportError)  # noqa E305


class IIndentationError(ISyntaxError):
    "Interface for `IndentationError`"


classImplements(IndentationError, IIndentationError)  # noqa E305


class IIndexError(ILookupError):
    "Interface for `IndexError`"


classImplements(IndexError, IIndexError)  # noqa E305


class IKeyError(ILookupError):
    "Interface for `KeyError`"


classImplements(KeyError, IKeyError)  # noqa E305


class IKeyboardInterrupt(IStandardError):
    "Interface for `KeyboardInterrupt`"


classImplements(KeyboardInterrupt, IKeyboardInterrupt)  # noqa E305


class IMemoryError(IStandardError):
    "Interface for `MemoryError`"


classImplements(MemoryError, IMemoryError)  # noqa E305


class INameError(IStandardError):
    "Interface for `NameError`"


classImplements(NameError, INameError)  # noqa E305


class INotImplementedError(IRuntimeError):
    "Interface for `NotImplementedError`"


classImplements(NotImplementedError, INotImplementedError)  # noqa E305


class IOSError(IEnvironmentError):
    "Interface for `OSError`"


classImplements(OSError, IOSError)  # noqa E305


class IOverflowError(IArithmeticError):
    "Interface for `ArithmeticError`"


classImplements(OverflowError, IOverflowError)  # noqa E305


class IOverflowWarning(IWarning):
    """Deprecated, no standard class implements this.

    This was the interface for ``OverflowWarning`` prior to Python 2.5,
    but that class was removed for all versions after that.
    """


class IReferenceError(IStandardError):
    "Interface for `ReferenceError`"


classImplements(ReferenceError, IReferenceError)  # noqa E305


class IRuntimeWarning(IWarning):
    "Interface for `RuntimeWarning`"


classImplements(RuntimeWarning, IRuntimeWarning)  # noqa E305


class IStopIteration(IException):
    "Interface for `StopIteration`"


classImplements(StopIteration, IStopIteration)  # noqa E305


class ISyntaxWarning(IWarning):
    "Interface for `SyntaxWarning`"


classImplements(SyntaxWarning, ISyntaxWarning)  # noqa E305


class ISystemError(IStandardError):
    "Interface for `SystemError`"


classImplements(SystemError, ISystemError)  # noqa E305


class ISystemExit(IException):
    "Interface for `SystemExit`"


classImplements(SystemExit, ISystemExit)  # noqa E305


class ITabError(IIndentationError):
    "Interface for `TabError`"


classImplements(TabError, ITabError)  # noqa E305


class ITypeError(IStandardError):
    "Interface for `TypeError`"


classImplements(TypeError, ITypeError)  # noqa E305


class IUnboundLocalError(INameError):
    "Interface for `UnboundLocalError`"


classImplements(UnboundLocalError, IUnboundLocalError)  # noqa E305


class IUnicodeError(IValueError):
    "Interface for `UnicodeError`"


classImplements(UnicodeError, IUnicodeError)  # noqa E305


class IUserWarning(IWarning):
    "Interface for `UserWarning`"


classImplements(UserWarning, IUserWarning)  # noqa E305


class IZeroDivisionError(IArithmeticError):
    "Interface for `ZeroDivisionError`"


classImplements(ZeroDivisionError, IZeroDivisionError)  # noqa E305
