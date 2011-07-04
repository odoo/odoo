# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010 OpenERP s.a. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

__all__ = ['partial', 'wraps', 'update_wrapper', 'synchronized']

try:
    from functools import partial, wraps, update_wrapper
except ImportError:
    # The functools module doesn't exist in python < 2.5
    # Code taken from python 2.5
    # http://svn.python.org/view/python/tags/r254/Lib/functools.py?view=markup

    def partial(fun, *args, **kwargs):
        """ Partial implementation
        
            See: http://svn.python.org/view/python/tags/r254/Lib/functools.py
        """
        def _partial(*args2, **kwargs2):
            return fun(*(args+args2), **dict(kwargs, **kwargs2))
        return _partial

    ### --- code from python 2.5

    # update_wrapper() and wraps() are tools to help write
    # wrapper functions that can handle naive introspection

    WRAPPER_ASSIGNMENTS = ('__module__', '__name__', '__doc__')
    WRAPPER_UPDATES = ('__dict__',)
    def update_wrapper(wrapper,
                       wrapped,
                       assigned = WRAPPER_ASSIGNMENTS,
                       updated = WRAPPER_UPDATES):
        """Update a wrapper function to look like the wrapped function

           wrapper is the function to be updated
           wrapped is the original function
           assigned is a tuple naming the attributes assigned directly
           from the wrapped function to the wrapper function (defaults to
           functools.WRAPPER_ASSIGNMENTS)
           updated is a tuple naming the attributes off the wrapper that
           are updated with the corresponding attribute from the wrapped
           function (defaults to functools.WRAPPER_UPDATES)
        """
        for attr in assigned:
            setattr(wrapper, attr, getattr(wrapped, attr))
        for attr in updated:
            getattr(wrapper, attr).update(getattr(wrapped, attr, {}))
        # Return the wrapper so this can be used as a decorator via partial()
        return wrapper

    def wraps(wrapped,
              assigned = WRAPPER_ASSIGNMENTS,
              updated = WRAPPER_UPDATES):
        """Decorator factory to apply update_wrapper() to a wrapper function

           Returns a decorator that invokes update_wrapper() with the decorated
           function as the wrapper argument and the arguments to wraps() as the
           remaining arguments. Default arguments are as for update_wrapper().
           This is a convenience function to simplify applying partial() to
           update_wrapper().
        """
        return partial(update_wrapper, wrapped=wrapped,
                       assigned=assigned, updated=updated)



def synchronized(lock_attr='_lock'):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            lock = getattr(self, lock_attr)
            try:
                lock.acquire()
                return func(self, *args, **kwargs)
            finally:
                lock.release()
        return wrapper
    return decorator



from inspect import getsourcefile

def frame_codeinfo(fframe, back=0):
    """ Return a (filename, line) pair for a previous frame .
        @return (filename, lineno) where lineno is either int or string==''
    """
    
    try:
        if not fframe:
            return ("<unknown>", '')
        for i in range(back):
            fframe = fframe.f_back
        try:
            fname = getsourcefile(fframe)
        except TypeError:
            fname = '<builtin>'
        lineno = fframe.f_lineno or ''
        return (fname, lineno)
    except Exception:
        return ("<unknown>", '')
