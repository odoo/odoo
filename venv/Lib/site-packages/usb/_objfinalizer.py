# -*- coding: utf-8 -*-
#
# Copyright 2009-2017 Wander Lairson Costa
# Copyright 2009-2021 PyUSB contributors
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import sys

__all__ = ['AutoFinalizedObject']


class _AutoFinalizedObjectBase(object):
    """
    Base class for objects that get automatically
    finalized on delete or at exit.
    """

    def _finalize_object(self):
        """Actually finalizes the object (frees allocated resources etc.).

        Returns: None

        Derived classes should implement this.
        """
        pass

    def __new__(cls, *args, **kwargs):
        """Creates a new object instance and adds the private finalizer
        attributes to it.

        Returns: new object instance

        Arguments:
        * *args, **kwargs -- ignored
        """
        instance = super(_AutoFinalizedObjectBase, cls).__new__(cls)
        instance._finalize_called = False
        return instance

    def _do_finalize_object(self):
        """Helper method that finalizes the object if not already done.

        Returns: None
        """
        if not self._finalize_called: # race-free?
            self._finalize_called = True
            self._finalize_object()

    def finalize(self):
        """Finalizes the object if not already done.

        Returns: None
        """
        # this is the "public" finalize method
        raise NotImplementedError(
            "finalize() must be implemented by AutoFinalizedObject."
        )

    def __del__(self):
        self.finalize()


if sys.hexversion >= 0x3040000:
    # python >= 3.4: use weakref.finalize
    import weakref

    def _do_finalize_object_ref(obj_ref):
        """Helper function for weakref.finalize() that dereferences a weakref
        to an object and calls its _do_finalize_object() method if the object
        is still alive. Does nothing otherwise.

        Returns: None (implicit)

        Arguments:
        * obj_ref -- weakref to an object
        """
        obj = obj_ref()
        if obj is not None:
            # else object disappeared
            obj._do_finalize_object()


    class AutoFinalizedObject(_AutoFinalizedObjectBase):

        def __new__(cls, *args, **kwargs):
            """Creates a new object instance and adds the private finalizer
            attributes to it.

            Returns: new object instance

            Arguments:
            * *args, **kwargs -- passed to the parent instance creator
                                 (which ignores them)
            """
            # Note:   Do not pass a (hard) reference to instance to the
            #         finalizer as func/args/kwargs, it'd keep the object
            #         alive until the program terminates.
            #         A weak reference is fine.
            #
            # Note 2: When using weakrefs and not calling finalize() in
            #         __del__, the object may already have disappeared
            #         when weakref.finalize() kicks in.
            #         Make sure that _finalizer() gets called,
            #         i.e. keep __del__() from the base class.
            #
            # Note 3: the _finalize_called attribute is (probably) useless
            #         for this class
            instance = super(AutoFinalizedObject, cls).__new__(
                cls, *args, **kwargs
            )

            instance._finalizer = weakref.finalize(
                instance, _do_finalize_object_ref, weakref.ref(instance)
            )

            return instance

        def finalize(self):
            """Finalizes the object if not already done."""
            self._finalizer()


else:
    # python < 3.4: keep the old behavior (rely on __del__),
    #                but don't call _finalize_object() more than once

    class AutoFinalizedObject(_AutoFinalizedObjectBase):

        def finalize(self):
            """Finalizes the object if not already done."""
            self._do_finalize_object()
