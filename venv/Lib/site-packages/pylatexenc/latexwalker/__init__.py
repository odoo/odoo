# -*- coding: utf-8 -*-
#
# The MIT License (MIT)
# 
# Copyright (c) 2018 Philippe Faist
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

r'''
The ``latexwalker`` module provides a simple API for parsing LaTeX snippets,
and representing the contents using a data structure based on node classes.

LatexWalker will understand the syntax of most common macros.  However,
``latexwalker`` is NOT a replacement for a full LaTeX engine.  (Originally,
``latexwalker`` was designed to extract useful text for indexing for text
database searches of LaTeX content.)

Simple example usage::

    >>> from pylatexenc.latexwalker import LatexWalker, LatexEnvironmentNode
    >>> w = LatexWalker(r"""
    ... \textbf{Hi there!} Here is \emph{a list}:
    ... \begin{enumerate}[label=(i)]
    ... \item One
    ... \item Two
    ... \end{enumerate}
    ... and $x$ is a variable.
    ... """)
    >>> (nodelist, pos, len_) = w.get_latex_nodes(pos=0)
    >>> nodelist[0]
    LatexCharsNode(pos=0, len=1, chars='\n')
    >>> nodelist[1]
    LatexMacroNode(pos=1, len=18, macroname='textbf',
    nodeargd=ParsedMacroArgs(argnlist=[LatexGroupNode(pos=8, len=11,
    nodelist=[LatexCharsNode(pos=9, len=9, chars='Hi there!')],
    delimiters=('{', '}'))], argspec='{'), macro_post_space='')
    >>> nodelist[5].isNodeType(LatexEnvironmentNode)
    True
    >>> nodelist[5].environmentname
    'enumerate'
    >>> nodelist[5].nodeargd.argspec
    '['
    >>> nodelist[5].nodeargd.argnlist
    [LatexGroupNode(pos=60, len=11, nodelist=[LatexCharsNode(pos=61, len=9,
    chars='label=(i)')], delimiters=('[', ']'))]
    >>> nodelist[7].latex_verbatim()
    '$x$'

You can also use `latexwalker` directly in command-line, producing JSON or a
human-readable node tree::

    $ echo '\textit{italic} text' | latexwalker --output-format=json
    {
      "nodelist": [
        {
          "nodetype": "LatexMacroNode",
          "pos": 0,
          "len": 15,
          "macroname": "textit",
    [...]

    $ latexwalker --help
    [...]

The parser can be influenced by specifying a collection of known macros and
environments (the "latex context") that are specified using
:py:class:`pylatexenc.macrospec.MacroSpec` and
:py:class:`pylatexenc.macrospec.EnvironmentSpec` objects in a
:py:class:`pylatexenc.macrospec.LatexContextDb` object.  See the doc of the
module :py:mod:`pylatexenc.macrospec` for more information.
'''

from __future__ import print_function, unicode_literals

import re
import sys
import logging
import json

import pylatexenc
from .. import macrospec
from .. import _util

if sys.version_info.major > 2:
    # Py3
    def unicode(string): return string
    _basestring = str
    _str_from_unicode = lambda x: x
    _unicode_from_str = lambda x: x
else:
    # Py2
    _basestring = basestring
    _str_from_unicode = lambda x: unicode(x).encode('utf-8')
    _unicode_from_str = lambda x: x.decode('utf-8')

logger = logging.getLogger(__name__)


def _maketuple(*args):
    # for use with Python 2, where we don't have *args expansion in tuples and
    # lists
    return tuple(args)


class LatexWalkerError(Exception):
    """
    Generic exception class raised by this module.
    """
    pass

class LatexWalkerParseError(LatexWalkerError):
    """
    Represents an error while parsing LaTeX code.

    The following attributes are available if they were provided to the class
    constructor:

    .. py:attribute:: msg

       The error message

    .. py:attribute:: s

       The string that was currently being parsed

    .. py:attribute:: pos
    
       The index in the string where the error occurred, starting at zero.

    .. py:attribute:: lineno

       The line number where the error occurred, starting at 1.

    .. py:attribute:: colno

       The column number where the error occurred in the line `lineno`, starting
       at 1.
    """
    def __init__(self, msg, s=None, pos=None, lineno=None, colno=None):
        self.input_source = None # attribute can be set to add to error msg display
        self.msg = msg
        self.s = s
        self.pos = pos
        self.lineno = lineno
        self.colno = colno
        self.open_contexts = []

        super(LatexWalkerParseError, self).__init__(self._dispstr())

    def _dispstr(self):
        msg = self.msg
        if self.input_source:
            msg += '  in {}'.format(self.input_source)
        disp = msg + " %s"%(self._fmt_pos(self.pos, self.lineno, self.colno))
        if self.open_contexts:
            disp += '\nOpen LaTeX blocks:\n'
            for context in reversed(self.open_contexts):
                what, pos, lineno, colno = context
                disp += '{empty:8}{loc:>10}  {what}\n'.format(empty='',
                                                        loc=self._fmt_pos(pos,lineno,colno),
                                                        what=what)
        return disp

    def _fmt_pos(self, pos, lineno, colno):
        if lineno is not None:
            if colno is not None:
                return '@(%d,%d)'%(lineno, colno)
            return '@%d'%(lineno)
        return '@ char %d'%(pos)

    def __str__(self):
        return self._dispstr()




class LatexWalkerEndOfStream(LatexWalkerError):
    """
    Reached end of input stream (e.g., end of file).
    """
    def __init__(self, final_space=''):
        super(LatexWalkerEndOfStream, self).__init__()
        self.final_space = final_space






def get_default_latex_context_db():
    r"""
    Return a :py:class:`pylatexenc.macrospec.LatexContextDb` instance
    initialized with a collection of known macros and environments.

    TODO: document categories.

    If you want to add your own definitions, you should use the
    :py:meth:`pylatexenc.macrospec.LatexContextDb.add_context_category()`
    method.  If you would like to override some definitions, use that method
    with the argument `prepend=True`.  See docs for
    :py:meth:`pylatexenc.macrospec.LatexContextDb.add_context_category()`.

    If there are too many macro/environment definitions, or if there are some
    irrelevant ones, you can always filter the returned database using
    :py:meth:`pylatexenc.macrospec.LatexContextDb.filter_context()`.

    .. versionadded:: 2.0
 
       The :py:class:`pylatexenc.macrospec.LatexContextDb` class as well as this
       method, were all introduced in `pylatexenc 2.0`.
    """
    db = macrospec.LatexContextDb()
    
    from ._defaultspecs import specs

    for cat, catspecs in specs:
        db.add_context_category(cat,
                                macros=catspecs['macros'],
                                environments=catspecs['environments'],
                                specials=catspecs['specials'])
    
    return db
    





# provide an interface compatibile with pylatexenc 1.x
def MacrosDef(macname, optarg, numargs):
    r"""
    .. deprecated:: 2.0

       Use :py:func:`pylatexenc.macrospec.std_macro` instead which does the same
       thing, or invoke the :py:class:`~pylatexenc.macrospec.MacroSpec` class
       directly (or a subclass).

       In `pylatexenc 1.x`, `MacrosDef` was a class.  Since `pylatexenc 2.0`,
       `MacrosDef` is a function which returns a
       :py:class:`~pylatexenc.macrospec.MacroSpec` instance.  In this way the
       earlier idiom ``MacrosDef(...)`` still works in `pylatexenc 2`.  The
       field names of the constructed object might have changed since
       `pylatexenc 1.x`, so you might have to adapt existing code if you were
       accessing individual fields of `MacrosDef` objects.

       In the object returned by `MacrosDef()`, we provide the legacy attributes
       `macname`, `optarg`, and `numargs`, so that existing code accessing those
       properties can continue to work.
    """
    _util.pylatexenc_deprecated_2(
        "`pylatexenc.latexwalker.MacrosDef` is now obsolete. "
        "It should still work in most use cases, but new code should use "
        "`pylatexenc.macrospec.MacroSpec` instead."
    )

    m = macrospec.std_macro(macname, optarg, numargs)
    # make accessible legacy attributes
    m.macname = m.macroname
    m.optarg = optarg
    m.numargs = numargs
    # also, make the macro args parser ignore any leading '*'-s to emulate
    # pylatexenc 1.x behavior
    m.args_parser._like_pylatexenc1x_ignore_leading_star = True
    return m


default_macro_dict = _util.LazyDict(
    generate_dict_fn=lambda: dict([
        (m.macroname, m)
        for m in get_default_latex_context_db().iter_macro_specs()
    ])
)
r"""
.. deprecated:: 2.0

   Use :py:func:`get_default_latex_context_db()` instead, or create your own
   :py:class:`pylatexenc.macrospec.LatexContextDb` object.


Provide an access to the default macro specs for `latexwalker` in a form
that is compatible with `pylatexenc 1.x`\ 's `default_macro_dict` module-level
dictionary.

This is implemented using a custom lazy mutable mapping, which behaves just like
a regular dictionary but that loads the data only once the dictionary is
accessed.  In this way the default latex specs into a python dictionary unless
they are actually queried or modified, and thus users of `pylatexenc 2.0` that
don't rely on the default macro/environment definitions shouldn't notice any
decrease in performance.
"""



# ------------------------------------------------


class LatexToken(object):
    r"""
    Represents a token read from the LaTeX input.

    This is used internally by :py:class:`LatexWalker`'s methods.  You probably
    don't need to worry about individual tokens.  Rather, you should use the
    high-level functions provided by :py:class:`LatexWalker` (e.g.,
    :py:meth:`~LatexWalker.get_latex_nodes()`).  So most likely, you can ignore
    this class entirely.

    Instances of this class are what the method
    :py:meth:`LatexWalker.get_token()` returns.  See the doc of that function
    for more information on how tokens are parsed.

    This is not the same thing as a LaTeX token, it's just a part of the input
    which we treat in the same way (e.g. a bunch of content characters, a
    comment, a macro, etc.)

    Information about the object is stored into the fields `tok` and `arg`. The
    `tok` field is a string which identifies the type of the token. The `arg`
    depends on what `tok` is, and describes the actual input.

    Additionally, this class stores information about the position of the token
    in the input stream in the field `pos`.  This `pos` is an integer which
    corresponds to the index in the input string.  The field `len` stores the
    length of the token in the input string.  This means that this token spans
    in the input string from `pos` to `pos+len`.

    Leading whitespace before the token is not returned as a separate
    'char'-type token, but it is given in the `pre_space` field of the token
    which follows.  Pre-space may contain a newline, but not two consecutive
    newlines.

    The `post_space` is only used for 'macro' and 'comment' tokens, and it
    stores any spaces encountered after a macro, or the newline with any
    following spaces that terminates a LaTeX comment.  When we encounter two
    consecutive newlines these are not included in `post_space`.

    The `tok` field may be one of:

      - 'char': raw character(s) which have no special LaTeX meaning and which
        are part of the text content.
        
        The `arg` field contains the characters themselves.

      - 'macro': a macro invocation, but not ``\begin`` or ``\end``
        
        The `arg` field contains the name of the macro, without the leading
        backslash.

      - 'begin_environment': an invocation of ``\begin{environment}``.
        
        The `arg` field contains the name of the environment inside the braces.

      - 'end_environment': an invocation of ``\end{environment}``.
        
        The `arg` field contains the name of the environment inside the braces.

      - 'comment': a LaTeX comment delimited by a percent sign up to the end of
        the line.
        
        The `arg` field contains the text in the comment line, not including the
        percent sign nor the newline.

      - 'brace_open': an opening brace.  This is usually a curly brace, and
        sometimes also a square bracket.  What is parsed as a brace depends on
        the arguments to :py:meth:`~LatexWalker.get_token()`.
        
        The `arg` is a string which contains the relevant brace character.
        
      - 'brace_close': a closing brace.  This is usually a curly brace, and
        sometimes also a square bracket.  What is parsed as a brace depends on
        the arguments to :py:meth:`~LatexWalker.get_token()`.
        
        The `arg` is a string which contains the relevant brace character.

      - 'mathmode_inline': a delimiter which starts/ends inline math.  This is
        (e.g.) a single '$' character which is not part of a double '$$'
        display environment delimiter.

        The `arg` is the string value of the delimiter in question ('$')

      - 'mathmode_display': a delimiter which starts/ends display math, e.g.,
        ``\[``.

        The `arg` is the string value of the delimiter in question (e.g.,
        ``\[`` or ``$$``)

      - 'specials': a character or character sequence that has a special
        meaning in LaTeX.  E.g., '~', '&', etc.

        The `arg` field is then the corresponding
        :py:class:`~pylatexenc.macrospec.SpecialsSpec` instance.  [The rationale
        for setting `arg` to a `SpecialsSpec` instance, in contrast to the
        behavior for macros and envrionments, is that macros and environments
        are delimited directly by LaTeX syntax and are determined unambiguously
        without any lookup in the latex context database.  This is not the case
        for specials.]
    """
    def __init__(self, tok, arg, pos, len, pre_space, post_space=''):
        self.tok = tok
        self.arg = arg
        self.pos = pos
        self.len = len
        self.pre_space = pre_space
        self.post_space = post_space
        self._fields = ['tok', 'arg', 'pos', 'len', 'pre_space']
        if self.tok in ('macro', 'comment'):
            self._fields.append('post_space')
        super(LatexToken, self).__init__()


    def __unicode__(self):
        return _unicode_from_str(self.__str__())

    def __repr__(self):
        return (
            "LatexToken(" +
            ", ".join([ "%s=%r"%(k,getattr(self,k))
                        for k in self._fields ]) +
            ")"
            )

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return all( ( getattr(self, f) == getattr(other, f)  for f in self._fields ) )

    # see https://docs.python.org/3/library/constants.html#NotImplemented
    def __ne__(self, other): return NotImplemented

    __hash__ = None


# ------------------------------------------------







class LatexNode(object):
    """
    Represents an abstract 'node' of the latex document.

    Use :py:meth:`nodeType()` to figure out what type of node this is, and
    :py:meth:`isNodeType()` to test whether it is of a given type.

    You should use :py:meth:`LatexWalker.make_node()` to create nodes, so that
    the latex walker has the opportunity to do some additional setting up.

    All nodes have the following attributes:

    .. py:attribute:: parsing_state

       The parsing state at the time this node was created.  This object stores
       additional context information for this node, such as whether or not this
       node was parsed in a math mode block of LaTeX code.

       See also the :py:meth:`LatexWalker.make_parsing_state()` and the
       `parsing_state` argument of :py:meth:`LatexWalker.get_latex_nodes()`.

    .. py:attribute:: pos

       The position in the parsed string that this node represents.  The parsed
       string can be recovered as `parsing_state.s`, see
       :py:attr:`ParsingState.s`.

    .. py:attribute:: len

       How many characters in the parsed string this node represents, starting
       at position `pos`.  The parsed string can be recovered as
       `parsing_state.s`, see :py:attr:`ParsingState.s`.

    .. versionadded:: 2.0
       
       The attributes `parsing_state`, `pos` and `len` were added in
       `pylatexenc 2.0`.
    """
    def __init__(self, _fields, _redundant_fields=None,
                 parsing_state=None, pos=None, len=None, **kwargs):

        # Important: subclasses must specify a list of fields they set in the
        # `_fields` argument.  They should only specify base (non-redundant)
        # fields; if they have "redundant" fields, specify the additional fields
        # in _redundant_fields=...
        super(LatexNode, self).__init__(**kwargs)

        self.parsing_state = parsing_state
        self.pos = pos
        self.len = len

        self._fields = tuple(['pos', 'len'] + list(_fields))
        if _redundant_fields is not None:
            self._redundant_fields = tuple(list(self._fields) + list(_redundant_fields))
        else:
            self._redundant_fields = self._fields

    def nodeType(self):
        """
        Returns the class which corresponds to the type of this node.  This is a
        Python class object, that is one of
        :py:class:`~pylatexenc.latexwalker.LatexCharsNode`,
        :py:class:`~pylatexenc.latexwalker.LatexGroupNode`, etc.
        """
        return LatexNode

    def isNodeType(self, t):
        """
        Returns `True` if the current node is of the given type.  The argument `t`
        must be a Python class such as,
        e.g. :py:class:`~pylatexenc.latexwalker.LatexGroupNode`.
        """
        return isinstance(self, t)

    def latex_verbatim(self):
        r"""
        Return the chunk of LaTeX code that this node represents.

        This is a shorthand for ``node.parsing_state.s[node.pos:node.pos+node.len]``.
        """
        if self.parsing_state is None:
            raise TypeError("Can't use latex_verbatim() on node because we don't "
                            "have any parsing_state set")
        return self.parsing_state.s[self.pos : self.pos+self.len]

    def __eq__(self, other):
        return other is not None  and  \
            self.nodeType() == other.nodeType()  and  \
            other.parsing_state is self.parsing_state and \
            other.pos == self.pos and \
            other.len == self.len and \
            all(
                ( getattr(self, f) == getattr(other, f)  for f in self._fields )
            )

    # see https://docs.python.org/3/library/constants.html#NotImplemented
    def __ne__(self, other): return NotImplemented

    __hash__ = None

    def __unicode__(self):
        return _unicode_from_str(self.__str__())
    def __str__(self):
        return self.__repr__()
    def __repr__(self):
        return (
            self.nodeType().__name__ + "(" +
            "parsing_state=<parsing state {}>, ".format(id(self.parsing_state)) +
            ", ".join([ "%s=%r"%(k,getattr(self,k))  for k in self._fields ]) +
            ")"
            )


class LatexCharsNode(LatexNode):
    """
    A string of characters in the LaTeX document, without any special LaTeX
    code.

    .. py:attribute:: chars

       The string of characters represented by this node.
    """
    def __init__(self, chars, **kwargs):
        super(LatexCharsNode, self).__init__(
            _fields = ('chars',),
            **kwargs
        )
        self.chars = chars

    def nodeType(self):
        return LatexCharsNode

class LatexGroupNode(LatexNode):
    r"""
    A LaTeX group delimited by braces, ``{like this}``.

    Note: in the case of an optional macro or environment argument, this node is
    also used to represents a group delimited by square braces instead of curly
    braces.

    .. py:attribute:: nodelist

       A list of nodes describing the contents of the LaTeX braced group.  Each
       item of the list is a :py:class:`LatexNode`.

    .. py:attribute:: delimiters

       A 2-item tuple that stores the delimiters for this group node.  Usually
       this is `('{', '}')`, except for optional macro arguments where this
       might be for instance `('[', ']')`.

       .. versionadded:: 2.0

          The `delimiters` field was added in `pylatexenc 2.0`.
    """
    def __init__(self, nodelist, **kwargs):
        delimiters = kwargs.pop('delimiters', ('{', '}'))
        super(LatexGroupNode, self).__init__(
            _fields=('nodelist','delimiters',),
            **kwargs
        )
        self.nodelist = nodelist
        self.delimiters = delimiters

    def nodeType(self):
        return LatexGroupNode

class LatexCommentNode(LatexNode):
    r"""
    A LaTeX comment, delimited by a percent sign until the end of line.

    .. py:attribute:: comment

       The comment string, not including the '%' sign nor the following newline

    .. py:attribute:: comment_post_space

       The newline that terminated the comment possibly followed by spaces
       (e.g., indentation spaces of the next line)

    """
    def __init__(self, comment, **kwargs):
        comment_post_space = kwargs.pop('comment_post_space', '')

        super(LatexCommentNode, self).__init__(
            _fields = ('comment', 'comment_post_space', ),
            **kwargs
        )

        self.comment = comment
        self.comment_post_space = comment_post_space

    def nodeType(self):
        return LatexCommentNode

class LatexMacroNode(LatexNode):
    r"""
    Represents a macro type node, e.g. ``\textbf``

    .. py:attribute:: macroname

       The name of the macro (string), *without* the leading backslash.

    .. py:attribute:: nodeargd

       The :py:class:`pylatexenc.macrospec.ParsedMacroArgs` object that
       represents the macro arguments.

       For macros that do not accept any argument, this is an empty
       :py:class:`~pylatexenc.macrospec.ParsedMacroArgs` instance.  The
       attribute `nodeargd` can be `None` even for macros that accept arguments,
       in the situation where :py:meth:`LatexWalker.get_latex_expression()`
       encounters the macro when reading a single expression.

       Arguments must be declared in the latex context passed to the
       :py:class:`LatexWalker` constructor, using a suitable
       :py:class:`pylatexenc.macrospec.MacroSpec` object.  Some known macros are
       already declared in the default latex context.

       .. versionadded:: 2.0

          The `nodeargd` attribute was introduced in `pylatexenc 2`.

    .. py:attribute:: macro_post_space

       Any spaces that were encountered immediately after the macro.

    The following attributes are obsolete since `pylatexenc 2.0`.

    .. py:attribute:: nodeoptarg

       .. deprecated:: 2.0

          Macro arguments are stored in `nodeargd` in `pylatexenc 2`.  Accessing
          the argument `nodeoptarg` will still give a first optional argument
          for standard latex macros, for backwards compatibility.

       If non-`None`, this corresponds to the optional argument of the macro.

    .. py:attribute:: nodeargs

       .. deprecated:: 2.0

          Macro arguments are stored in `nodeargd` in pylatexenc 2.  Accessing
          the argument `nodeargs` will still provide a list of argument nodes
          for standard latex macros, for backwards compatibility.

       A list of arguments to the macro. Each item in the list is a
       :py:class:`LatexNode`.
    """
    def __init__(self, macroname, **kwargs):
        nodeargd=kwargs.pop('nodeargd', macrospec.ParsedMacroArgs())
        macro_post_space=kwargs.pop('macro_post_space', '')
        # legacy:
        nodeoptarg=kwargs.pop('nodeoptarg', None)
        nodeargs=kwargs.pop('nodeargs', [])

        super(LatexMacroNode, self).__init__(
            _fields = ('macroname','nodeargd','macro_post_space'),
            _redundant_fields = ('nodeoptarg','nodeargs'),
            **kwargs)

        self.macroname = macroname
        self.nodeargd = nodeargd
        self.macro_post_space = macro_post_space
        # legacy:
        self.nodeoptarg = nodeoptarg
        self.nodeargs = nodeargs

    def nodeType(self):
        return LatexMacroNode



class LatexEnvironmentNode(LatexNode):
    r"""
    A LaTeX Environment Node, i.e. ``\begin{something} ... \end{something}``.

    .. py:attribute:: environmentname

       The name of the environment ('itemize', 'equation', ...)

    .. py:attribute:: nodelist

       A list of :py:class:`LatexNode`'s that represent all the contents between
       the ``\begin{...}`` instruction and the ``\end{...}`` instruction.

    .. py:attribute:: nodeargd

       The :py:class:`pylatexenc.macrospec.ParsedMacroArgs` object that
       represents the arguments passed to the environment.  These are arguments
       that are present after the ``\begin{xxxxxx}`` command, as in
       ``\begin{tabular}{ccc}`` or ``\begin{figure}[H]``.  Arguments must be
       declared in the latex context passed to the :py:class:`LatexWalker`
       constructor, using a suitable
       :py:class:`pylatexenc.macrospec.EnvironmentSpec` object.  Some known
       environments are already declared in the default latex context.

       .. versionadded:: 2.0

          The `nodeargd` attribute was introduced in `pylatexenc 2`.

    The following attributes are available, but they are obsolete since
    `pylatexenc 2.0`.

    .. py:attribute:: envname

       .. deprecated:: 2.0

          This attribute was renamed `environmentname` for consistency with the
          rest of the package.

    .. py:attribute:: optargs

       .. deprecated:: 2.0

          Macro arguments are stored in `nodeargd` in `pylatexenc 2`.  Accessing
          the argument `optargs` will still give a list of initial optional
          arguments for standard latex macros, for backwards compatibility.

    .. py:attribute:: args

       .. deprecated:: 2.0

          Macro arguments are stored in `nodeargd` in `pylatexenc 2`.  Accessing
          the argument `args` will still give a list of curly-brace-delimited
          arguments for standard latex macros, for backwards compatibility.
    """
    
    def __init__(self, environmentname, nodelist, **kwargs):
        nodeargd = kwargs.pop('nodeargd', macrospec.ParsedMacroArgs())
        # legacy:
        optargs = kwargs.pop('optargs', [])
        args = kwargs.pop('args', [])

        super(LatexEnvironmentNode, self).__init__(
            _fields = ('environmentname','nodelist','nodeargd',),
            _redundant_fields = ('envname', 'optargs','args',),
            **kwargs)

        self.environmentname = environmentname
        self.nodelist = nodelist
        self.nodeargd = nodeargd
        # legacy:
        self.envname = environmentname
        self.optargs = optargs
        self.args = args

    def nodeType(self):
        return LatexEnvironmentNode

class LatexSpecialsNode(LatexNode):
    r"""
    Represents a specials type node, e.g. ``&`` or ``~``

    .. py:attribute:: specials_chars

       The name of the specials (string), *without* the leading backslash.

    .. py:attribute:: nodeargd

       If the specials spec (cf. :py:class:`~pylatexenc.macrospec.SpecialsSpec`)
       has `args_parser=None` then the attribute `nodeargd` is set to `None`.
       If `args_parser` is specified in the spec, then the attribute `nodeargd`
       is a :py:class:`pylatexenc.macrospec.ParsedMacroArgs` instance that 
       represents the arguments to the specials.

       The `nodeargd` attribute can also be `None` even if the specials expects
       arguments, in the special situation where
       :py:meth:`LatexWalker.get_latex_expression()` encounters this specials.

       Arguments must be declared in the latex context passed to the
       :py:class:`LatexWalker` constructor, using a suitable
       :py:class:`pylatexenc.macrospec.SpecialsSpec` object.  Some known latex
       specials are already declared in the default latex context.

    .. versionadded:: 2.0

       Latex specials were introduced in `pylatexenc 2.0`.
    """
    def __init__(self, specials_chars, **kwargs):
        nodeargd=kwargs.pop('nodeargd', None)

        super(LatexSpecialsNode, self).__init__(
            _fields = ('specials_chars','nodeargd'),
            **kwargs)

        self.specials_chars = specials_chars
        self.nodeargd = nodeargd

    def nodeType(self):
        return LatexSpecialsNode




class LatexMathNode(LatexNode):
    r"""
    A Math node type.

    Note that currently only 'inline' math environments are detected.

    .. py:attribute:: displaytype

       Either 'inline' or 'display', to indicate an inline math block or a
       display math block. (Note that math environments such as
       ``\begin{equation}...\end{equation}``, are reported as
       :py:class:`LatexEnvironmentNode`'s, and not as
       :py:class:`LatexMathNode`'s.)

    .. py:attribute:: delimiters

       A 2-item tuple containing the begin and end delimiters used to delimit
       this math mode section.

       .. versionadded:: 2.0

          The `delimiters` attribute was introduced in `pylatexenc 2`.

    .. py:attribute:: nodelist
    
       The contents of the environment, given as a list of
       :py:class:`LatexNode`'s.
    """
    def __init__(self, displaytype, nodelist=[], **kwargs):
        delimiters = kwargs.pop('delimiters', (None, None))

        super(LatexMathNode, self).__init__(
            _fields = ('displaytype','nodelist','delimiters'),
            **kwargs
        )

        self.displaytype = displaytype
        self.nodelist = nodelist
        self.delimiters = delimiters

    def nodeType(self):
        return LatexMathNode


# ------------------------------------------------------------------------------


class _PushPropOverride(object):
    def __init__(self, obj, propname, new_value):
        super(_PushPropOverride, self).__init__()
        self.obj = obj
        self.propname = propname
        self.new_value = new_value

    def __enter__(self):
        if self.new_value is not None:
            self.initval = getattr(self.obj, self.propname)
            setattr(self.obj, self.propname, self.new_value)
        return self

    def __exit__(self, type, value, traceback):
        # clean-up
        if self.new_value is not None:
            setattr(self.obj, self.propname, self.initval)


class ParsingState(object):
    r"""
    Stores some information about the current parsing state, such as whether we
    are currently in a math mode block.

    One of the ideas of `pylatexenc` is to make the parsing of LaTeX code mostly
    state-independent mark-up parsing (in contrast to a full TeX engine, whose
    state constantly changes and whose parsing behavior is altered dynamically
    while parsing).  However a minimal state of the context might come in handy
    sometimes.  Perhaps some macros or specials should behave differently in
    math mode than in text mode.

    This class also stores some essential information that is associated with
    :py:class:`LatexNode`\ 's and which provides a context to better understand
    the node structure.  For instance, we store the original parsed string, and
    each node refers to which part of the string they represent.
    
    .. py:attribute:: s

       The string that is parsed by the :py:class:`LatexWalker`

    .. py:attribute:: latex_context

       The latex context (with macros/environments specifications) that was used
       when parsing the string `s`.  This is a
       :py:class:`pylatexenc.macrospec.LatexContextDb` object.

    .. py:attribute:: in_math_mode

       Whether or not we are in a math mode chunk of LaTeX (True or False).
       This can be inline or display, and can be caused by an equation
       environment.

    .. py:attribute:: math_mode_delimiter

       Information about the kind of math mode we are currently in, if
       `in_math_mode` is `True`.  This is a string which can be set to aid the
       parser.  The parser sets this field to the math mode delimiter that
       initiated the math mode (one of ``'$'``, ``'$$'``, ``r'\('``, ``r'\)'``).
       For user-initiated math modes (e.g. by a custom environment definition),
       you can set this string to any custom value EXCEPT any of the core math
       mode delimiters listed above.

       .. note:: The tokenizer/parser relies on the value of the
                 `math_mode_delimiter` attribute to disambiguate two consecutive
                 dollar signs ``...$$...`` into either a display math mode
                 delimiter or two inline math mode delimiters (as in
                 ``$a$$b$``).  You should only set `math_mode_delimiter='$'` if
                 you know what you're doing.

    .. versionadded:: 2.0
 
       This class was introduced in version 2.0.

    .. versionadded:: 2.7

       The attribute `math_mode_delimiter` was introduced in version 2.7.

    .. versionchanged:: 2.7

       All arguments must now be specified as keyword arguments as of version
       2.7.
    """
    def __init__(self, **kwargs):
        super(ParsingState, self).__init__()
        self.s = None
        self.latex_context = None
        self.in_math_mode = False
        self.math_mode_delimiter = None
        self._fields = ('s', 'latex_context', 'in_math_mode', 'math_mode_delimiter', )

        do_sanitize = kwargs.pop('_do_sanitize', True)

        self._set_fields(kwargs, do_sanitize=do_sanitize)

    def sub_context(self, **kwargs):
        r"""
        Return a new :py:class:`ParsingState` instance that is a copy of the current
        parsing state, but where the given properties keys have been set to the
        corresponding values (given as keyword arguments).

        This makes it easy to create a sub-context in a given parser.  For
        instance, if we enter math mode, we might write::

           parsing_state_inner = parsing_state.sub_context(in_math_mode=True)

        If no arguments are provided, this returns a copy of the present parsing
        context object.
        """
        p = self.__class__(_do_sanitize=False, **self.get_fields())

        p._set_fields(kwargs)

        return p

    def get_fields(self):
        r"""
        Returns the fields and values associated with this `ParsingState` as a
        dictionary.
        """
        return dict([(f, getattr(self, f)) for f in self._fields])


    def _set_fields(self, kwargs, do_sanitize=True):

        for k, v in kwargs.items():
            if k not in self._fields:
                raise ValueError("Invalid field for ParsingState: {}={!r}".format(k, v))
            setattr(self, k, v)

        if do_sanitize:
            # Do some sanitization.  If we set in_math_mode=False, then we should
            # clear any math_mode_delimiter.
            self._sanitize(given_fields=kwargs)

    def _sanitize(self, given_fields):
        """
        Sanitize the parsing state.  E.g., clear any `math_mode_delimiter` if
        `in_math_mode` is `False`.

        The argument `given_fields` is what fields the user required to set;
        this is used to generate warnings if incompatible field configurations
        were explicitly required to be set.
        """
        if not self.in_math_mode and self.math_mode_delimiter:
            self.math_mode_delimiter = None
            if 'math_mode_delimiter' in given_fields:
                logger.warning(
                    "ParsingState: You set math_mode_delimiter=%r but "
                    "in_math_mode is False", self.math_mode_delimiter
                )




# ------------------------------------------------------------------------------



class LatexWalker(object):
    r"""
    A parser which walks through an input stream, parsing it as LaTeX markup.

    Arguments:

      - `s`: the string to parse as LaTeX code

      - `latex_context`: a :py:class:`pylatexenc.macrospec.LatexContextDb`
        object that provides macro and environment specifications with
        instructions on how to parse arguments, etc.  If you don't specify this
        argument, or if you specify `None`, then the default database is used.
        The default database is obtained with
        :py:func:`get_default_latex_context_db()`.

        .. versionadded:: 2.0

           This `latex_context` argument was introduced in version 2.0.

    Additional keyword arguments are flags which influence the parsing.
    Accepted flags are:

      - `tolerant_parsing=True|False` If set to `True`, then the parser
        generally ignores syntax errors rather than raising an exception.

      - `strict_braces=True|False` This option refers specifically to reading a
        encountering a closing brace when an expression is needed.  You
        generally won't need to specify this flag, use `tolerant_parsing`
        instead.

    The methods provided in this class perform various parsing of the given
    string `s`.  These methods typically accept a `pos` parameter, which must be
    an integer, which defines the position in the string `s` to start parsing.

    These methods, unless otherwise documented, return a tuple `(node, pos,
    len)`, where node is a :py:class:`LatexNode` describing the parsed content,
    `pos` is the position at which the LaTeX element of iterest was encountered,
    and `len` is the length of the string that is considered to be part of the
    `node`.  That is, the position in the string that is immediately after the
    node is `pos+len`.

    The following obsolete flag is accepted by the constructor for backwards
    compatibility with `pylatexenc 1.x`:

      - `macro_dict`: This argument is kept for compatibility with `pylatexenc
        1.x`.  This is a dictionary of known LaTeX macro specifications.  If
        specified, this should be a dictionary where the keys are macro names
        and values are :py:class:`pylatexenc.macrospec.MacroSpec` instances, as
        returned for instance by the `pylatexenc 1.x`-emulating function
        :py:func:`MacrosDef`.  If you specify this argument, you cannot provide
        a custom `latex_context`.  This argument is superseded by the
        `latex_context` argument.  Furthermore, if you specify this argument, no
        specials are parsed so that the behavior closer to `pylatexenc 1.x`.

        .. deprecated:: 2.0
    
           The `macro_dict` argument has been replaced by the much more powerful
           `latex_context` argument which allows you to further provide
           environment specifications, etc.
    
      - `keep_inline_math=True|False`: Obsolete option.  In `pylatexenc 1.x`,
        this option triggered a weird behavior especially since there is a
        similarly named option in
        :py:class:`pylatexenc.latex2text.LatexNodes2Text` with a different
        meaning.  [See `Issue #14
        <https://github.com/phfaist/pylatexenc/issues/14>`_.]  You should now
        only use the option `math_mode=` in
        :py:class:`pylatexenc.latex2text.LatexNodes2Text`.

        .. deprecated:: 2.0

           This option is ignored starting from `pylatexenc 2`.  Instead, you
           should set the option `math_mode=` accordingly in
           :py:class:`pylatexenc.latex2text.LatexNodes2Text`.


    .. py:attribute:: s
    
       The string that is being parsed.

       Do NOT modify this attribute.
    """

    def __init__(self, s, latex_context=None, **kwargs):

        self.s = s

        # will be determined lazily automatically by pos_to_lineno_colno(...)
        self._line_no_calc = None

        self.debug_nodes = False

        if latex_context is None:
            if 'macro_dict' in kwargs:
                # LEGACY -- build a latex context using the given macro_dict
                _util.pylatexenc_deprecated_2(
                    "The `macro_dict=...` option in LatexWalker() is obsolete since "
                    "pylatexenc 2.  It'll still work, but please consider using instead "
                    "the more versatile option `latex_context=...`."
                )

                macro_dict = kwargs.pop('macro_dict', None)

                default_latex_context = get_default_latex_context_db()

                latex_context = default_latex_context.filter_context(
                    keep_which=['environments'], # no specials
                )
                latex_context.add_context_category(
                    'custom',
                    macro_dict.values(),
                    default_latex_context.iter_environment_specs()
                )

            else:
                # default -- use default
                latex_context = get_default_latex_context_db()

        else:
            # make sure the user didn't also provide a macro_dict= argument
            if 'macro_dict' in kwargs:
                raise TypeError(
                    "Cannot specify both `latex_context=` and `macro_dict=` arguments"
                )


        # We don't store the latex_context in an attribute, because we always
        # access it via the current parsing_state

        self.default_parsing_state = ParsingState(
            s=self.s,
            latex_context=latex_context,
        )


        #
        # now parsing flags:
        #
        self.tolerant_parsing = kwargs.pop('tolerant_parsing', True)
        self.strict_braces = kwargs.pop('strict_braces', False)

        if 'keep_inline_math' in kwargs:
            _util.pylatexenc_deprecated_2(
                "The keep_inline_math=... option in LatexWalker() has no effect "
                "in pylatexenc 2.  Please consider using the more versatile option "
                "math_mode=... in LatexNodes2Text() instead."
            )
            del kwargs['keep_inline_math']

        if kwargs:
            # any flags left which we haven't recognized
            logger.warning("LatexWalker(): Unknown flag(s) encountered: %r", kwargs.keys())

        super(LatexWalker, self).__init__()


    def make_parsing_state(self, **kwargs):
        r"""
        Return a new parsing state object that corresponds to the current string
        that we are parsing (`s` provided to the constructor) and the current
        latex context (`latex_context` provided to the constructor).

        If no arguments are provided, this returns the default parsing state.

        If keyword arguments are provided, then they can override fields from
        the default parsing state.  For instance, if we enter math mode, you
        might use::
        
          parsing_state_mathmode = \
              my_latex_walker.make_parsing_state(in_math_mode=True)
        """
        return self.default_parsing_state.sub_context(**kwargs)

    def parse_flags(self):
        """
        The parse flags currently set on this object.  Returns a dictionary with
        keys 'keep_inline_math', 'tolerant_parsing' and 'strict_braces'.

        .. deprecated:: 2.0

           The 'keep_inline_math' key is always set to `None` starting in
           `pylatexenc 2` and might be removed entirely in future versions.
        """
        return {
            'tolerant_parsing': self.tolerant_parsing,
            'strict_braces': self.strict_braces,
            # compatibility with pylatexenc 1.x
            'keep_inline_math': None,
        }

    def _report_ignore_parse_error(self, exc):
        logger.info("Ignoring parse error (tolerant parsing mode): %s", exc)
        
    def get_token(self, pos, include_brace_chars=None, environments=True,
                  keep_inline_math=None, parsing_state=None, **kwargs):
        r"""
        Parses the latex content given to the constructor (and stored in `self.s`),
        starting at position `pos`, to parse a single "token", as defined by
        :py:class:`LatexToken`.

        Parse the token in the stream pointed to at position `pos`.

        For tokens of type 'char', usually a single character is returned.  The
        only exception is at paragraph boundaries, where a single 'char'-type
        token has argument '\\n\\n'.

        Returns a :py:class:`LatexToken`. Raises
        :py:exc:`LatexWalkerEndOfStream` if end of stream reached.

        The argument `include_brace_chars=` allows to specify additional pairs
        of single characters which should be considered as braces (i.e., of
        'brace_open' and 'brace_close' token types).  It should be a list of
        2-item tuples, for instance ``[('[', ']'), ('<', '>')]``.  The pair
        `('{', '}')` is always considered as braces.  The delimiters may not
        have more than one character each.

        If `environments=False`, then ``\begin`` and ``\end`` tokens count as
        regular 'macro' tokens (see :py:class:`LatexToken`); otherwise (the
        default) they are considered as the token types 'begin_environment' and
        'end_environment'.

        The parsing of the tokens might be influcenced by the `parsing_state` (a
        :py:class:`ParsingState` instance).  Currently, the only influence this
        has is that some latex specials are parsed differently if in math mode.
        See doc for :py:class:`ParsingState`.  If `parsing_state` is `None`, the
        default parsing state returned by :py:meth:`make_parsing_state()` is
        used.

        .. deprecated:: 2.0

           The flag `keep_inline_math` is only accepted for compatibiltiy with
           earlier versions of `pylatexenc`, but it has no effect starting in
           `pylatexenc 2`.  See the :py:class:`LatexWalker` class doc.

        .. deprecated:: 2.0

           If `brackets_are_chars=False`, then square bracket characters count
           as 'brace_open' and 'brace_close' token types (see
           :py:class:`LatexToken`); otherwise (the default) they are considered
           just like other normal characters.

        .. versionadded:: 2.0

           The `parsing_state` argument was introduced in version 2.0.
        """

        if parsing_state is None:
            parsing_state = self.make_parsing_state() # get default parsing state

        brace_chars = [('{', '}')]

        if include_brace_chars:
            brace_chars += include_brace_chars

        if 'brackets_are_chars' in kwargs:
            if not kwargs.pop('brackets_are_chars'):
                brace_chars += [('[', ']')]

        s = self.s # shorthand

        space = '' # space that we gobble up before token

        #
        # In tolerant parsing mode, this method should not raise
        # LatexWalkerParseError.  Instead, it should return whatever token (at
        # the worst case, a placeholder chars token) it can to help the caller
        # recover from errors.
        #
        # This is because we want to recover from errors as soon as possible.
        # For instance a macro argument parser might rely on calls to
        # get_token() to parse its command arguments (say check for a starred
        # command); if an exception is raised then it will bubble up and make it
        # harder to keep the macro in some meaningful way.  We could have
        # required instead to guard each call to get_token with a try/except
        # block but it feels better to keep the same philosophy as internal
        # calls to get_latex_expression(), etc., which simply return whatever
        # they can instead of raising exceptions in tolerant parsing mode.
        #
        def _token_parse_error(msg, len, placeholder):
            e = LatexWalkerParseError(
                s=s,
                pos=pos,
                msg=msg,
                **self.pos_to_lineno_colno(pos, as_dict=True)
            )
            if self.tolerant_parsing:
                self._report_ignore_parse_error(e)
                return None, LatexToken(
                    tok='char',
                    arg=placeholder,
                    pos=pos,
                    len=len,
                    pre_space=space
                )
            return e, None

        while pos < len(s) and s[pos].isspace():
            space += s[pos]
            pos += 1
            if space.endswith('\n\n'):  # two \n's indicate new paragraph.
                return LatexToken(tok='char', arg='\n\n', pos=pos-2, len=2,
                                  pre_space=space[:-2])

        if pos >= len(s):
            raise LatexWalkerEndOfStream(final_space=space)

        if s[pos] == '\\':
            # escape sequence
            if pos+1 >= len(s):
                raise LatexWalkerEndOfStream()
            macro = s[pos+1] # next char is necessarily part of macro
            # following chars part of macro only if all are alphabetical
            isalphamacro = False
            i = 2
            if s[pos+1].isalpha():
                isalphamacro = True
                while pos+i<len(s) and s[pos+i].isalpha():
                    macro += s[pos+i]
                    i += 1

            # special treatment for \( ... \) and \[ ... \] -- "macros" for
            # inline/display math modes
            if macro in ['[', ']']:
                return LatexToken(tok='mathmode_display', arg='\\'+macro,
                                  pos=pos, len=i, pre_space=space)
            if macro in ['(', ')']:
                return LatexToken(tok='mathmode_inline', arg='\\'+macro,
                                  pos=pos, len=i, pre_space=space)

            # see if we have a begin/end environment
            if environments and macro in ['begin', 'end']:
                # \begin{environment} or \end{environment}
                envmatch = re.match(r'^\s*\{([\w* ._-]+)\}', s[pos+i:])
                if envmatch is None:
                    e, t = _token_parse_error(
                        msg=r"Bad \{} macro: expected {{environmentname}}".format(macro),
                        len=i,
                        placeholder='\\'+macro
                    )
                    if e:
                        raise e
                    return t

                return LatexToken(
                    tok=('begin_environment' if macro == 'begin' else 'end_environment'),
                    arg=envmatch.group(1),
                    pos=pos,
                    len=i+envmatch.end(), # !!: envmatch.end() counts from pos+i
                    pre_space=space
                    )

            # get the following whitespace, and store it in the macro's post_space
            post_space = ''
            if isalphamacro:
                # important, LaTeX does not consume space after non-alpha macros, like \&
                while pos+i<len(s) and s[pos+i].isspace():
                    post_space += s[pos+i]
                    i += 1
                    if post_space.endswith('\n\n'):
                        # if two \n's are encountered this signals a new
                        # paragraph, so do not include them as part of the
                        # macro's post_space.
                        post_space = post_space[:-2]
                        i -= 2
                        break

            return LatexToken(tok='macro', arg=macro, pos=pos, len=i,
                              pre_space=space, post_space=post_space)

        if s[pos] == '%':
            # latex comment
            m = re.compile(r'(\n|\r|\n\r)(?P<extraspace>\s*)').search(s, pos)
            mlen = None
            if m is not None:
                if m.group('extraspace').startswith( ('\n', '\r', '\n\r',) ):
                    # special case where there is a \n immediately following the
                    # first one -- this is a new paragraph
                    arglen = m.start()-pos
                    mlen = m.start()-pos
                    mspace = ''
                else:
                    arglen = m.start()-pos
                    mlen = m.end()-pos
                    mspace = m.group()
            else:
                arglen = len(s)-pos# [  ==len(s[pos:])  ]
                mlen = arglen
                mspace = ''
            return LatexToken(tok='comment', arg=s[pos+1:pos+arglen], pos=pos, len=mlen,
                              pre_space=space, post_space=mspace)

        # see https://stackoverflow.com/a/19343/1694896
        openbracechars, closebracechars = zip(*brace_chars)

        if s[pos] in openbracechars:
            return LatexToken(tok='brace_open', arg=s[pos], pos=pos, len=1, pre_space=space)

        if s[pos] in closebracechars:
            return LatexToken(tok='brace_close', arg=s[pos], pos=pos, len=1, pre_space=space)

        # check for math-mode dollar signs.  Using python syntax
        # "string.startswith(pattern, pos)"
        if s.startswith('$$', pos):
            # if we are in an open '$'-delimited math mode, we need to parse $$
            # as two single $'s (issue #43)
            if not (parsing_state.in_math_mode and parsing_state.math_mode_delimiter == '$'):
                return LatexToken(tok='mathmode_display', arg='$$',
                                  pos=pos, len=2, pre_space=space)
        if s.startswith('$', pos):
            return LatexToken(tok='mathmode_inline', arg='$', pos=pos, len=1, pre_space=space)

        sspec = parsing_state.latex_context.test_for_specials(
            s, pos, parsing_state=parsing_state
        )
        if sspec is not None:
            return LatexToken(tok='specials', arg=sspec,
                              pos=pos, len=len(sspec.specials_chars), pre_space=space)

        # otherwise, the token is a normal 'char' type.

        return LatexToken(tok='char', arg=s[pos], pos=pos, len=1, pre_space=space)


    def make_node(self, node_class, **kwargs):
        r"""
        Create and return a node of type `node_class` which holds a representation
        of the latex code at position `pos` and of length `len` in the parsed
        string.

        The node class should be a :py:class:`LatexNode` subclass.  Keyword
        arguments are supplied directly to the constructor of the node class.

        Mandatory keyword-only arguments are 'pos', 'len', and 'parsing_state'.

        All nodes produced by :py:meth:`get_latex_nodes()` and friends use this
        method to create node classes.

        .. versionadded:: 2.0
        
           This method was introduced in `pylatexenc 2.0`.
        """
        # mandatory keyword-only arguments:
        pos, len, parsing_state = \
            kwargs.pop('pos'), kwargs.pop('len'), kwargs.pop('parsing_state')

        node = node_class(pos=pos, len=len, parsing_state=parsing_state, **kwargs)
        if self.debug_nodes:
            logger.debug("New node: %r", node)
        return node

    def _mknodeposlen(self, nclass, parsing_state, pos, len, **kwargs):
        return (
            self.make_node(nclass, parsing_state=parsing_state, pos=pos, len=len, **kwargs),
            pos,
            len
        )

    
    def pos_to_lineno_colno(self, pos, as_dict=False):
        r"""
        Return the line and column number corresponding to the given `pos` in our
        string `self.s`.

        The first time this function is called, line numbers are calculated for
        the entire string.  These are cached for future calls which are then
        fast.

        Return a tuple `(lineno, colno)` giving line number and column number.
        Line numbers start at 1 and column numbers start at zero, i.e., the
        beginning of the document (`pos=0`) has line and column number `(1,0)`.
        If `as_dict=True`, then a dictionary with keys 'lineno', 'colno' is
        returned instead of a tuple.
        """

        if self._line_no_calc is None:
            self._line_no_calc = _util.LineNumbersCalculator(self.s)

        return self._line_no_calc.pos_to_lineno_colno(pos, as_dict=as_dict)


    def get_latex_expression(self, pos, strict_braces=None, parsing_state=None):
        r"""
        Parses the latex content given to the constructor (and stored in `self.s`),
        starting at position `pos`, to parse a single LaTeX expression.

        Reads a latex expression, e.g. macro argument. This may be a single char, an escape
        sequence, or a expression placed in braces.  This is what TeX calls a "token" (and
        not what we call a token... anyway).

        Parsing might be influenced by the `parsing_state`.  See doc for
        :py:class:`ParsingState`.  If `parsing_state` is `None`, then the
        default parsing state is used.

        Returns a tuple `(node, pos, len)`, where `pos` is the position of the
        first char of the expression and `len` the length of the expression.

        .. versionadded:: 2.0

           The `parsing_state` argument was introduced in version 2.0.
        """

        if parsing_state is None:
            parsing_state = self.make_parsing_state() # get default parsing state

        with _PushPropOverride(self, 'strict_braces', strict_braces):

            tok = self.get_token(pos, environments=False, parsing_state=parsing_state)

            if tok.tok == 'macro':
                if tok.arg == 'end':
                    if not self.tolerant_parsing:
                        # error, we were expecting a single token
                        raise LatexWalkerParseError(
                            r"Expected expression, got \end",
                            self.s, pos,
                            **self.pos_to_lineno_colno(pos, as_dict=True))
                    else:
                        return self._mknodeposlen(LatexCharsNode,
                                                  parsing_state=parsing_state,
                                                  chars='',
                                                  pos=tok.pos,
                                                  len=0)
                return self._mknodeposlen(LatexMacroNode,
                                          parsing_state=parsing_state,
                                          macroname=tok.arg,
                                          nodeargd=None,
                                          macro_post_space=tok.post_space,
                                          nodeoptarg=None, nodeargs=None,
                                          pos=tok.pos, len=tok.len)
            if tok.tok == 'specials':
                return self._mknodeposlen(LatexSpecialsNode,
                                          parsing_state=parsing_state,
                                          specials_chars=tok.arg.specials_chars,
                                          nodeargd=None,
                                          pos=tok.pos, len=tok.len)
            if tok.tok == 'comment':
                return self.get_latex_expression(tok.pos+tok.len, parsing_state=parsing_state)
            if tok.tok == 'brace_open':
                return self.get_latex_braced_group(tok.pos, parsing_state=parsing_state)
            if tok.tok == 'brace_close':
                # don't worry, stray closing braces are still reported (in
                # get_latex_nodes()) if tolerant_parsing=False even if
                # strict_braces=False.  That's because we leave the brace in the
                # input and it will be picked up when we read the next token.
                if self.strict_braces and not self.tolerant_parsing:
                    raise LatexWalkerParseError(
                        "Expected expression, got closing brace '{}'".format(tok.arg),
                        self.s, pos,
                        **self.pos_to_lineno_colno(pos, as_dict=True)
                    )
                return self._mknodeposlen(LatexCharsNode,
                                          parsing_state=parsing_state,
                                          chars='',
                                          pos=tok.pos, len=0)
            if tok.tok == 'char':
                return self._mknodeposlen(LatexCharsNode,
                                          parsing_state=parsing_state,
                                          chars=tok.arg,
                                          pos=tok.pos,
                                          len=tok.len)
            if tok.tok in ('mathmode_inline', 'mathmode_display'):
                # don't report a math mode token, treat as char or macro
                if tok.arg.startswith('\\'):
                    return self._mknodeposlen(LatexMacroNode,
                                              parsing_state=parsing_state,
                                              macroname=tok.arg,
                                              nodeoptarg=None,
                                              nodeargs=None,
                                              macro_post_space=tok.post_space,
                                              pos=tok.pos,
                                              len=tok.len)
                else:
                    return self._mknodeposlen(LatexCharsNode,
                                              parsing_state=parsing_state,
                                              chars=tok.arg,
                                              pos=tok.pos,
                                              len=tok.len)

            raise LatexWalkerParseError(
                "Unknown token type: {}".format(tok.tok), self.s, pos,
                **self.pos_to_lineno_colno(pos, as_dict=True))


    def get_latex_maybe_optional_arg(self, pos, parsing_state=None):
        r"""
        Parses the latex content given to the constructor (and stored in `self.s`),
        starting at position `pos`, to attempt to parse an optional argument.

        Parsing might be influenced by the `parsing_state`. See doc for
        :py:class:`ParsingState`.  If `parsing_state` is `None`, the default
        parsing state is used.

        Attempts to parse an optional argument. If this is successful, we return
        a tuple `(node, pos, len)` if success where `node` is a
        :py:class:`LatexGroupNode`.  Otherwise, this method returns None.

        .. versionadded:: 2.0

           The `parsing_state` argument was introduced in version 2.0.
        """

        if parsing_state is None:
            parsing_state = self.make_parsing_state() # get default parsing state

        try:
            tok = self.get_token(pos, include_brace_chars=[('[', ']')], environments=False,
                                 parsing_state=parsing_state)
        except LatexWalkerEndOfStream:
            # we're at end of stream, simply report no optional arg and let
            # parents re-detect end of stream when they call again get_token().
            # Added exception handler to fix issue #57
            return None

        if tok.tok == 'brace_open' and tok.arg == '[':
            return self.get_latex_braced_group(pos, brace_type='[',
                                               parsing_state=parsing_state)

        return None


    def get_latex_braced_group(self, pos, brace_type='{', parsing_state=None):
        r"""
        Parses the latex content given to the constructor (and stored in `self.s`),
        starting at position `pos`, to read a latex group delimited by braces.

        Reads a latex expression enclosed in braces ``{ ... }``. The first token of
        `s[pos:]` must be an opening brace.

        Parsing might be influenced by the `parsing_state`.  See doc for
        :py:class:`ParsingState`.  If `parsing_state` is `None`, the default
        parsing state is used.

        Returns a tuple `(node, pos, len)`, where `node` is a
        :py:class:`LatexGroupNode` instance, `pos` is the position of the first
        char of the expression (which has to be an opening brace), and `len` is
        the length of the group, including the closing brace (relative to the
        starting position).

        The group must be delimited by the given `brace_type`.  `brace_type` may
        be one of ``{``, ``[``, ``(`` or ``<``, or a 2-item tuple of two
        distinct single characters providing the opening and closing brace
        chars (e.g., ``("<", ">")``).

        .. versionadded:: 2.0

           The `parsing_state` argument was introduced in version 2.0.
        """

        if parsing_state is None:
            parsing_state = self.make_parsing_state() # get default parsing state

        closing_brace = None
        if brace_type == '{':
            closing_brace = '}'
        elif brace_type == '[':
            closing_brace = ']'
        elif brace_type == '(':
            closing_brace = ')'
        elif brace_type == '<':
            closing_brace = '>'
        elif len(brace_type) == 2:
            brace_type, closing_brace = brace_type
        else:
            raise ValueError("Invalid brace type for get_latex_braced_group(): %s" %(brace_type))

        include_brace_chars = None
        if brace_type and brace_type != '{':
            include_brace_chars = [(brace_type, closing_brace)]

        firsttok = self.get_token(pos, include_brace_chars=include_brace_chars,
                                  parsing_state=parsing_state)
        if firsttok.tok != 'brace_open'  or  firsttok.arg != brace_type:
            raise LatexWalkerParseError(
                s=self.s,
                pos=pos,
                msg='get_latex_braced_group: not an opening brace/bracket: %s' %(self.s[pos]),
                **self.pos_to_lineno_colno(pos, as_dict=True)
            )

        (nodelist, npos, nlen) = self.get_latex_nodes(
            firsttok.pos + firsttok.len,
            stop_upon_closing_brace=(brace_type, closing_brace),
            parsing_state=parsing_state
        )

        return self._mknodeposlen(LatexGroupNode, nodelist=nodelist,
                                  parsing_state=parsing_state,
                                  delimiters=(brace_type, closing_brace),
                                  pos = firsttok.pos,
                                  len = npos + nlen - firsttok.pos)


    def get_latex_environment(self, pos, environmentname=None, parsing_state=None):
        r"""
        Parses the latex content given to the constructor (and stored in `self.s`),
        starting at position `pos`, to read a latex environment.

        Reads a latex expression enclosed in a
        ``\begin{environment}...\end{environment}``.  The first token in the
        stream must be the ``\begin{environment}``.

        If `environmentname` is given and nonempty, then additionally a
        :py:exc:`LatexWalkerParseError` is raised if the environment in the
        input stream does not match the provided environment name.

        Arguments to the begin environment command are parsed according to the
        corresponding specification in the given latex context `latex_context`
        provided to the constructor.  The environment name is looked up as a
        "macro name" in the macro spec.

        Parsing might be influenced by the `parsing_state`.  See doc for
        :py:class:`ParsingState`.  If `parsing_state` is `None`, the default
        parsing state is used.

        Returns a tuple (node, pos, len) where node is a
        :py:class:`LatexEnvironmentNode`.

        .. versionadded:: 2.0

           The `parsing_state` argument was introduced in version 2.0.
        """

        if parsing_state is None:
            parsing_state = self.make_parsing_state() # get default parsing state

        startpos = pos

        firsttok = self.get_token(pos, parsing_state=parsing_state)
        if firsttok.tok != 'begin_environment'  or  \
           (environmentname is not None and firsttok.arg != environmentname):
            raise LatexWalkerParseError(
                s=self.s,
                pos=pos,
                msg=r'get_latex_environment: expected \begin{%s}: %s' %(
                    environmentname if environmentname is not None else '<environment name>',
                    firsttok.arg
                ),
                **self.pos_to_lineno_colno(pos, as_dict=True)
            )
        if (environmentname is None):
            environmentname = firsttok.arg

        pos = firsttok.pos + firsttok.len

        env_spec = parsing_state.latex_context.get_environment_spec(environmentname)
        if env_spec is None:
            env_spec = macrospec.EnvironmentSpec('')

        # self = latex walker instance
        try:
            argsresult = env_spec.parse_args(w=self, pos=pos, parsing_state=parsing_state)
        except (LatexWalkerEndOfStream, LatexWalkerParseError) as e:
            e = self._exchandle_parse_subexpression(
                e,
                firsttok,
                "arguments of environment \"\\begin{{{}}}\"".format(environmentname),
            )
            if e is not None: raise e
            argsresult = (None, pos, 0, {})

        if len(argsresult) == 4:
            (argd, apos, alen, adic) = argsresult
        else:
            (argd, apos, alen) = argsresult
            adic = {}

        pos = apos + alen

        parsing_state_inner = adic.get('inner_parsing_state', parsing_state)
        #parsing_state_inner = parsing_state
        if env_spec.is_math_mode:
            parsing_state_inner = parsing_state.sub_context(
                in_math_mode=True,
                math_mode_delimiter='{'+environmentname+'}',
            )

        (nodelist, npos, nlen) = self.get_latex_nodes(pos,
                                                      stop_upon_end_environment=environmentname,
                                                      parsing_state=parsing_state_inner)

        if argd is not None and argd.legacy_nodeoptarg_nodeargs:
            legnodeoptarg = argd.legacy_nodeoptarg_nodeargs[0]
            legnodeargs = argd.legacy_nodeoptarg_nodeargs[1]
        else:
            legnodeoptarg, legnodeargs = None, []

        return self._mknodeposlen(LatexEnvironmentNode,
                                  parsing_state=parsing_state,
                                  environmentname=environmentname,
                                  nodelist=nodelist,
                                  nodeargd=argd,
                                  # legacy:
                                  optargs=[legnodeoptarg],
                                  args=legnodeargs,
                                  pos=startpos,
                                  len=npos+nlen-startpos)


    def _exchandle_parse_subexpression(self, e, tok, what):
        """
        (INTERNAL.) Handle an exception raised by a method that you called to parse
        a macro arguments or another "sub-expression".  Use as::

            except (LatexWalkerEndOfStream, LatexWalkerParseError) as e:
                e = self._exchandle_parse_subexpression(e, <tok>, "what this is about")
                if e is not None: raise e
                ... # do sth to recover from parse error in tolerant mode

        Use in an exception handler that captures both `LatexWalkerEndOfStream`
        and `LatexWalkerParseError`.  Returns what exception you should raise if
        you got one of these while parsing, e.g., macro arguments.
        """

        if isinstance(e, LatexWalkerEndOfStream):
            e = LatexWalkerParseError(
                s=self.s,
                pos=tok.pos,
                msg="End of input while parsing {}".format(what),
                **self.pos_to_lineno_colno(tok.pos, as_dict=True)
            )

        if getattr(e, 'pos', None) is not None and e.lineno is None and e.colno is None:
            e.lineno, e.colno = self.pos_to_lineno_colno(e.pos)

        e.open_contexts.append(
            _maketuple('{}'.format(what), tok.pos,
                       *self.pos_to_lineno_colno(tok.pos))
        )

        if self.tolerant_parsing:
            self._report_ignore_parse_error(e)
            return None
        return e
   

    def get_latex_nodes(self, pos=0, stop_upon_closing_brace=None,
                        stop_upon_end_environment=None,
                        stop_upon_closing_mathmode=None, read_max_nodes=None,
                        parsing_state=None):
        r"""
        Parses the latex content given to the constructor (and stored in `self.s`)
        into a list of nodes.

        Returns a tuple `(nodelist, pos, len)` where:

          - `nodelist` is a list of :py:class:`LatexNode`\ 's representing the
            parsed LaTeX code.

          - `pos` is the same as the `pos` given as argument; if there is
            leading whitespace it is reported in `nodelist` using a
            :py:class:`LatexCharsNode`.

          - `len` is the length of the parsed expression.  If one of the
            `stop_upon_...=` arguments are provided (cf below), then the `len`
            includes the length of the token/expression that stopped the
            parsing.
        
        If `stop_upon_closing_brace` is given and set to a character, then
        parsing stops once the given closing brace is encountered (but not
        inside a subgroup).  The brace is given as a character, ']', '}', ')',
        or '>'.  Alternatively you may specify a 2-item tuple of two single
        distinct characters representing the opening and closing brace chars.
        The returned `len` includes the closing brace, but the closing brace is
        not included in any of the nodes in the `nodelist`.

        If `stop_upon_end_environment` is provided, then parsing stops once the
        given environment was closed.  If there is an environment mismatch, then
        a `LatexWalkerParseError` is raised except in tolerant parsing mode (see
        :py:meth:`parse_flags()`).  Again, the closing environment is included
        in the length count but not the nodes.

        If `stop_upon_closing_mathmode` is specified, then the parsing stops
        once the corresponding math mode (assumed already open) is closed.  This
        argument may take the values `None` (no particular request to stop at
        any math mode token), or one of ``$``, ``$$``, ``\)`` or ``\]``
        indicating a closing math mode delimiter that we are expecting and at
        which point parsing should stop.

        If the token '$' (respectively '$$') is encountered, it is interpreted
        as the *beginning* of a new math mode chunk *unless* the argument
        `stop_upon_closing_mathmode=...` has been set to '$' (respectively
        '$$').

        If `read_max_nodes` is non-`None`, then it should be set to an integer
        specifying the maximum number of top-level nodes to read before
        returning.  (Top-level nodes means that macro arguments, environment or
        group contents, etc., do not count towards `read_max_nodes`.)  If
        `None`, the entire input string will be parsed.

        .. note::

           There are a few important differences between
           ``get_latex_nodes(read_max_nodes=1)`` and ``get_latex_expression()``:
           The former reads a logical node of the LaTeX document, which can be a
           sequence of characters, a macro invocation with arguments, or an
           entire environment, but the latter reads a single LaTeX "token" in
           a similar way to how LaTeX parses macro arguments.

           For instance, if a macro is encountered, then
           ``get_latex_nodes(read_max_nodes=1)`` will read and parse its
           arguments, and include it in the corresponding
           :py:class:`LatexMacroNode`, whereas ``get_latex_expression()`` will
           return a minimal :py:class:`LatexMacroNode` with no arguments
           regardless of the macro's argument specification.  The same holds for
           latex specials.  For environments,
           ``get_latex_nodes(read_max_nodes=1)`` will return the entire parsed
           environment into a :py:class:`LatexEnvironmentNode`, whereas
           ``get_latex_expression()`` will return a :py:class:`LatexMacroNode`
           named 'begin' with no arguments.

        Parsing might be influenced by the `parsing_state`.  See doc for
        :py:class:`ParsingState`.  If `parsing_state` is `None`, the default
        parsing state is used.

        .. versionadded:: 2.0

           The `parsing_state` argument was introduced in version 2.0.
        """

        if parsing_state is None:
            parsing_state = self.make_parsing_state() # get default parsing state

        nodelist = []
    
        include_brace_chars = None
        opening_brace_for_stop_upon_closing_brace = None
        if stop_upon_closing_brace:
            if stop_upon_closing_brace == '}':
                opening_brace_for_stop_upon_closing_brace = '{'
            elif stop_upon_closing_brace == ']':
                opening_brace_for_stop_upon_closing_brace = '['
            elif stop_upon_closing_brace == ')':
                opening_brace_for_stop_upon_closing_brace = '('
            elif stop_upon_closing_brace == '>':
                opening_brace_for_stop_upon_closing_brace = '<'
            elif len(stop_upon_closing_brace) == 2:
                opening_brace_for_stop_upon_closing_brace, stop_upon_closing_brace = \
                    stop_upon_closing_brace

            if stop_upon_closing_brace != '}':
                include_brace_chars = [
                    (opening_brace_for_stop_upon_closing_brace, stop_upon_closing_brace)
                ]

        # consistency check
        if stop_upon_closing_mathmode is not None and not parsing_state.in_math_mode:
            logger.warning(
                ("Call to LatexWalker.get_latex_nodes(stop_upon_closing_mathmode={!r}) "
                 "but parsing state has in_math_mode={!r}").format(
                     stop_upon_closing_mathmode,
                     parsing_state.in_math_mode,
                 )
            )

        #
        # Man, I really need to rewrite this function properly. This is some
        # pretty ugly sh*t.
        #

        origpos = pos

        class PosPointer:
            def __init__(self, pos, parsing_state, lastchars='', lastchars_pos=None):
                self.pos = pos
                self.parsing_state = parsing_state
                self.lastchars = lastchars
                self.lastchars_pos = lastchars_pos

            def push_lastchars(self, pos, chars):
                self.lastchars += chars
                if self.lastchars_pos is None:
                    self.lastchars_pos = pos
            
            def flush_lastchars(self):
                res = self.lastchars_pos, self.lastchars
                self.lastchars = ''
                self.lastchars_pos = None
                return res

        p = PosPointer(pos=pos, parsing_state=parsing_state)

        def do_read(nodelist, p):
            r"""
            Read a single token and process it, recursing into brace blocks and
            environments etc if needed, and appending stuff to nodelist.

            Return True whenever we should stop trying to read more. (e.g. upon
            reaching the a matched stop_upon_end_environment etc.)  Can return
            an exception instance to give more information than simply `True`.
            """

            try:
                tok = self.get_token(p.pos, include_brace_chars=include_brace_chars,
                                     parsing_state=p.parsing_state)
            except LatexWalkerEndOfStream as e:
                if self.tolerant_parsing:
                    return e
                raise # re-raise
            except LatexWalkerParseError as e:
                # get_token() should not raise parse errors in tolerant_parsing
                # mode, because this can lead to infinite loops (#37)
                assert(not self.tolerant_parsing)
                raise # exception will be handled in outer loop

            p.pos = tok.pos + tok.len

            #def tok_to_pos_and_chars_from_ppos(tok):
            #    return tok.pos, self.s[p.pos, tok.pos+tok.len]

            # if it's a char, just append it to the stream of last characters.
            if tok.tok == 'char':
                p.push_lastchars(pos=(tok.pos - len(tok.pre_space)),
                                 chars=(tok.pre_space + tok.arg))
                return False

            # if it's not a char, push the last `p.lastchars` into the node list
            # before we do anything else
            if len(p.lastchars):
                charspos, chars = p.flush_lastchars()
                strnode = self.make_node(LatexCharsNode,
                                         parsing_state=p.parsing_state,
                                         chars=chars+tok.pre_space,
                                         pos=charspos, len=tok.pos - charspos)
                nodelist.append(strnode)
                if read_max_nodes and len(nodelist) >= read_max_nodes:
                    # adjust p.pos for return value of get_latex_nodes()
                    p.pos = tok.pos
                    return True
            elif len(tok.pre_space):
                # If we have pre_space, add a separate chars node that contains
                # the spaces.  We do this seperately, so that latex2text can
                # ignore these groups by default to avoid too much space on the
                # output.  This allows latex2text to implement the
                # `strict_latex_spaces=True` flag correctly.
                spacestrnode = self.make_node(LatexCharsNode,
                                              parsing_state=p.parsing_state,
                                              chars=tok.pre_space,
                                              pos=tok.pos-len(tok.pre_space),
                                              len=len(tok.pre_space))
                nodelist.append(spacestrnode)
                if read_max_nodes and len(nodelist) >= read_max_nodes:
                    # adjust p.pos for return value of get_latex_nodes()
                    p.pos = tok.pos
                    return True

            # and see what the token is.

            if tok.tok == 'brace_close':
                # we've reached the end of the group. stop the parsing.
                if tok.arg != stop_upon_closing_brace:
                    #p.push_lastchars(tok_to_pos_and_chars_from_ppos(tok))
                    raise LatexWalkerParseError(
                        s=self.s,
                        pos=tok.pos,
                        msg="Unexpected mismatching closing brace: '%s'"%(tok.arg),
                        **self.pos_to_lineno_colno(tok.pos, as_dict=True)
                    )
                return True

            if tok.tok == 'end_environment':
                # we've reached the end of an environment.
                if not stop_upon_end_environment:
                    #p.push_lastchars(tok_to_pos_and_chars_from_ppos(tok))
                    raise LatexWalkerParseError(
                        s=self.s,
                        pos=tok.pos,
                        msg=("Unexpected closing environment: '{}'".format(tok.arg)),
                        **self.pos_to_lineno_colno(tok.pos, as_dict=True)
                    )
                elif tok.arg != stop_upon_end_environment:
                    #p.push_lastchars(tok_to_pos_and_chars_from_ppos(tok))
                    raise LatexWalkerParseError(
                        s=self.s,
                        pos=tok.pos,
                        msg=("Unexpected mismatching closing environment: '{}', "
                             "was expecting '{}'".format(tok.arg, stop_upon_end_environment)),
                        **self.pos_to_lineno_colno(tok.pos, as_dict=True)
                    )
                return True

            if tok.tok in ('mathmode_inline', 'mathmode_display'):
                # see if we need to stop at a math mode 
                if stop_upon_closing_mathmode is not None:
                    if tok.arg == stop_upon_closing_mathmode:
                        # all OK, found the closing mathmode.
                        return True
                    if tok.arg in [r'\)', r'\]']:
                        # this is definitely a closing math-mode delimiter, so
                        # not a new math mode block.  This is a parse error,
                        # because we need to match the given
                        # stop_upon_closing_mathmode mode.

                        #p.push_lastchars(tok_to_pos_and_chars_from_ppos(tok))
                        raise LatexWalkerParseError(
                            s=self.s,
                            pos=tok.pos,
                            msg="Mismatching closing math mode: '{}', expected '{}'".format(
                                tok.arg, stop_upon_closing_mathmode,
                            ),
                            **self.pos_to_lineno_colno(tok.pos, as_dict=True)
                        )
                    # all ok, this is a new math mode opening.  Keep an assert
                    # in case we forget to include some math-mode delimiters in
                    # the future.
                    assert tok.arg in ['$', '$$', r'\(', r'\[']
                elif tok.arg in [r'\)', r'\]']:
                    # unexpected close-math-mode delimiter, but no
                    # stop_upon_closing_mathmode was specified. Parse error.

                    #p.push_lastchars(tok_to_pos_and_chars_from_ppos(tok))
                    raise LatexWalkerParseError(
                        s=self.s,
                        pos=tok.pos,
                        msg="Unexpected closing math mode: '{}'".format(tok.arg),
                        **self.pos_to_lineno_colno(tok.pos, as_dict=True)
                    )

                # we have encountered a new math inline, parse the math expression

                corresponding_closing_mathmode = \
                    {r'\(': r'\)', r'\[': r'\]'}.get(tok.arg, tok.arg)
                displaytype = 'inline' if tok.arg in [r'\(', '$'] else 'display'

                parsing_state_inner = p.parsing_state.sub_context(
                    in_math_mode=True,
                    math_mode_delimiter=tok.arg
                )

                try:
                    (mathinline_nodelist, mpos, mlen) = self.get_latex_nodes(
                        p.pos,
                        stop_upon_closing_mathmode=corresponding_closing_mathmode,
                        parsing_state=parsing_state_inner
                    )
                except LatexWalkerParseError as e:
                    e.open_contexts.append( _maketuple('math mode "{}"'.format(tok.arg), tok.pos,
                                                       *self.pos_to_lineno_colno(tok.pos)) )
                    raise
                p.pos = mpos + mlen

                nodelist.append(self.make_node(
                    LatexMathNode,
                    parsing_state=p.parsing_state,
                    displaytype=displaytype,
                    nodelist=mathinline_nodelist,
                    delimiters=(tok.arg, corresponding_closing_mathmode),
                    pos=tok.pos, len=mpos+mlen-tok.pos
                ))
                if read_max_nodes and len(nodelist) >= read_max_nodes:
                    return True
                return

            if tok.tok == 'comment':
                commentnode = self.make_node(LatexCommentNode,
                                             parsing_state=p.parsing_state,
                                             comment=tok.arg,
                                             comment_post_space=tok.post_space,
                                             pos=tok.pos, len=tok.len)
                nodelist.append(commentnode)
                if read_max_nodes and len(nodelist) >= read_max_nodes:
                    return True
                return

            if tok.tok == 'brace_open':
                # another braced group to read.
                try:
                    (groupnode, bpos, blen) = self.get_latex_braced_group(
                        tok.pos,
                        brace_type=tok.arg,
                        parsing_state=p.parsing_state
                    )
                # except LatexWalkerEndOfStream as e:
                #     # shouldn't happen.
                except LatexWalkerParseError as e:
                    e.open_contexts.append( _maketuple('open brace', tok.pos,
                                                       *self.pos_to_lineno_colno(tok.pos)) )
                    raise

                p.pos = bpos + blen
                nodelist.append(groupnode)
                if read_max_nodes and len(nodelist) >= read_max_nodes:
                    return True
                return

            if tok.tok == 'begin_environment':
                # an environment to read.
                try:
                    (envnode, epos, elen) = self.get_latex_environment(
                        tok.pos,
                        environmentname=tok.arg,
                        parsing_state=p.parsing_state
                    )
                except LatexWalkerParseError as e:
                    e.open_contexts.append(
                        _maketuple('begin environment "{}"'.format(tok.arg), tok.pos,
                                   *self.pos_to_lineno_colno(tok.pos))
                    )
                    raise
                p.pos = epos + elen
                # add node and continue.
                nodelist.append(envnode)
                if read_max_nodes and len(nodelist) >= read_max_nodes:
                    return True
                return

            if tok.tok == 'macro':
                # read a macro. see if it has arguments.
                macroname = tok.arg
                mspec = p.parsing_state.latex_context.get_macro_spec(macroname)
                if mspec is None:
                    mspec = macrospec.MacroSpec('')

                try:
                    margsresult = \
                        mspec.parse_args(w=self, pos=tok.pos + tok.len,
                                         parsing_state=p.parsing_state)
                except (LatexWalkerEndOfStream, LatexWalkerParseError) as e:
                    e = self._exchandle_parse_subexpression(
                        e,
                        tok,
                        "arguments of macro \"{}\"".format(macroname)
                    )
                    if e is not None: raise e
                    margsresult = (None, tok.pos + tok.len, 0, {})

                if len(margsresult) == 4:
                    (nodeargd, mapos, malen, mdic) = margsresult
                else:
                    (nodeargd, mapos, malen) = margsresult
                    mdic = {}

                p.pos = mapos + malen

                if nodeargd is not None and nodeargd.legacy_nodeoptarg_nodeargs:
                    nodeoptarg = nodeargd.legacy_nodeoptarg_nodeargs[0]
                    nodeargs = nodeargd.legacy_nodeoptarg_nodeargs[1]
                else:
                    nodeoptarg, nodeargs = None, []
                node = self.make_node(LatexMacroNode,
                                      parsing_state=p.parsing_state,
                                      macroname=tok.arg,
                                      nodeargd=nodeargd,
                                      macro_post_space=tok.post_space,
                                      # legacy data:
                                      nodeoptarg=nodeoptarg,
                                      nodeargs=nodeargs,
                                      pos=tok.pos,
                                      len=p.pos-tok.pos)
                nodelist.append(node)

                if 'new_parsing_state' in mdic:
                    # modify current parsing state---
                    p.parsing_state = mdic['new_parsing_state']

                if read_max_nodes and len(nodelist) >= read_max_nodes:
                    return True
                return None

            if tok.tok == 'specials':
                # read the specials. see if it expects/has arguments.
                sspec = tok.arg

                p.pos = tok.pos + tok.len
                nodeargd = None

                try:
                    res = sspec.parse_args(w=self, pos=p.pos, parsing_state=p.parsing_state)
                except (LatexWalkerEndOfStream, LatexWalkerParseError) as e:
                    e = self._exchandle_parse_subexpression(
                        e,
                        tok,
                        "arguments of specials \"{}\"".format(sspec.specials_chars)
                    )
                    if e is not None: raise e
                    res = (None, p.pos, 0, {})

                if res is not None:
                    # specials expects arguments, read them
                    if len(res) == 4:
                        (nodeargd, mapos, malen, spdic) = res
                    else:
                        (nodeargd, mapos, malen) = res
                        spdic = {}

                    p.pos = mapos + malen

                else:
                    spdic = {}

                node = self.make_node(LatexSpecialsNode,
                                      parsing_state=p.parsing_state,
                                      specials_chars=sspec.specials_chars,
                                      nodeargd=nodeargd,
                                      pos=tok.pos,
                                      len=p.pos-tok.pos)
                nodelist.append(node)

                if 'new_parsing_state' in spdic:
                    # modify current parsing state---
                    p.parsing_state = spdic['new_parsing_state']

                if read_max_nodes and len(nodelist) >= read_max_nodes:
                    return True
                return None


            raise LatexWalkerParseError(
                s=self.s,
                pos=p.pos,
                msg="Unknown token: {!r}".format(tok),
                **self.pos_to_lineno_colno(p.pos, as_dict=True)
            )



        while True:
            try:
                # might return boolean or Exception object
                r_endnow = do_read(nodelist, p)
            except LatexWalkerEndOfStream as e:
                if stop_upon_closing_brace or stop_upon_end_environment \
                   or stop_upon_closing_mathmode:
                    # unexpected eof
                    if stop_upon_closing_brace:
                        expecting = "'"+stop_upon_closing_brace+"'"
                    elif stop_upon_end_environment:
                        expecting = r"\end{"+stop_upon_end_environment+"}"
                    elif stop_upon_closing_mathmode:
                        expecting = "'"+stop_upon_closing_mathmode+"'"
                    e = LatexWalkerParseError(
                        s=self.s,
                        pos=p.pos,
                        msg="Unexpected end of stream, was expecting {}"
                            .format(expecting),
                        **self.pos_to_lineno_colno(len(self.s), as_dict=True)
                    )
                    if self.tolerant_parsing:
                        self._report_ignore_parse_error(e)
                        r_endnow = True
                    else:
                        raise e
                else:
                    r_endnow = e
            except LatexWalkerParseError as e:
                if self.tolerant_parsing:
                    self._report_ignore_parse_error(e)
                    r_endnow = False
                else:
                    raise

            if r_endnow:

                # add last chars and last space
                if isinstance(r_endnow, LatexWalkerEndOfStream):
                    p.push_lastchars(pos=p.pos,
                                     chars=r_endnow.final_space)
                    p.pos += len(r_endnow.final_space)

                if p.lastchars:
                    charspos, chars = p.flush_lastchars()
                    strnode = self.make_node(LatexCharsNode,
                                             parsing_state=p.parsing_state,
                                             chars=chars,
                                             pos=charspos, len=len(chars))
                    nodelist.append(strnode)
                return (nodelist, origpos, p.pos - origpos)

        # code never reaches here

































    
    
# ------------------------------------------------------------------------------

def get_token(s, pos, brackets_are_chars=True, environments=True, **parse_flags):
    """
    Parse the next token in the stream.

    Returns a `LatexToken`. Raises `LatexWalkerEndOfStream` if end of stream reached.

    .. deprecated:: 1.0
       Please use :py:meth:`LatexWalker.get_token()` instead.
    """
    return LatexWalker(s, **parse_flags).get_token(pos=pos,
                                                   brackets_are_chars=brackets_are_chars,
                                                   environments=environments)


def get_latex_expression(s, pos, **parse_flags):
    """
    Reads a latex expression, e.g. macro argument. This may be a single char, an escape
    sequence, or a expression placed in braces.

    Returns a tuple `(<LatexNode instance>, pos, len)`. `pos` is the first char of the
    expression, and `len` is its length.

    .. deprecated:: 1.0
       Please use :py:meth:`LatexWalker.get_latex_expression()` instead.
    """

    return LatexWalker(s, **parse_flags).get_latex_expression(pos=pos)


def get_latex_maybe_optional_arg(s, pos, **parse_flags):
    """
    Attempts to parse an optional argument. Returns a tuple `(groupnode, pos, len)` if
    success, otherwise returns None.

    .. deprecated:: 1.0
       Please use :py:meth:`LatexWalker.get_latex_maybe_optional_arg()` instead.
    """

    return LatexWalker(s, **parse_flags).get_latex_maybe_optional_arg(pos=pos)

    
def get_latex_braced_group(s, pos, brace_type='{', **parse_flags):
    """
    Reads a latex expression enclosed in braces {...}. The first token of `s[pos:]` must
    be an opening brace.

    Returns a tuple `(node, pos, len)`. `pos` is the first char of the
    expression (which has to be an opening brace), and `len` is its length,
    including the closing brace.

    .. deprecated:: 1.0
       Please use :py:meth:`LatexWalker.get_latex_braced_group()` instead.
    """

    return LatexWalker(s, **parse_flags).get_latex_braced_group(pos=pos, brace_type=brace_type)


def get_latex_environment(s, pos, environmentname=None, **parse_flags):
    """
    Reads a latex expression enclosed in a \\begin{environment}...\\end{environment}. The first
    token in the stream must be the \\begin{environment}.

    Returns a tuple (node, pos, len) with node being a :py:class:`LatexEnvironmentNode`.

    .. deprecated:: 1.0
       Please use :py:meth:`LatexWalker.get_latex_environment()` instead.
    """

    return LatexWalker(s, **parse_flags).get_latex_environment(pos=pos,
                                                               environmentname=environmentname)

def get_latex_nodes(s, pos=0, stop_upon_closing_brace=None, stop_upon_end_environment=None,
                    stop_upon_closing_mathmode=None, **parse_flags):
    """
    Parses latex content `s`.

    Returns a tuple `(nodelist, pos, len)` where nodelist is a list of `LatexNode` 's.

    If `stop_upon_closing_brace` is given, then `len` includes the closing brace, but the
    closing brace is not included in any of the nodes in the `nodelist`.

    .. deprecated:: 1.0
       Please use :py:meth:`LatexWalker.get_latex_nodes()` instead.
    """

    return LatexWalker(s, **parse_flags).get_latex_nodes(
        stop_upon_closing_brace=stop_upon_closing_brace,
        stop_upon_end_environment=stop_upon_end_environment,
        stop_upon_closing_mathmode=stop_upon_closing_mathmode
    )










# ------------------------------------------------------------------------------

#
# small utilities for displaying & debugging
#


def nodelist_to_latex(nodelist):

    # It's NOT recommended to use this function.  You should use
    # node.latex_verbatim() instead.

    # Here, we don't use latex_verbatim() and continue to provide (an updated
    # version of) the old code, because we want to be compatible with code that
    # used this function on custom instantiated nodes without setting the
    # parsing_state.

    def add_args(nodeargd):
        if nodeargd is None or nodeargd.argspec is None or nodeargd.argnlist is None:
            return ''
        argslatex = ''
        for argt, argn in zip(nodeargd.argspec, nodeargd.argnlist):
            if argt == '*':
                if argn is not None:
                    argslatex += nodelist_to_latex([argn])
            elif argt == '[':
                if argn is not None:
                    # the node is a group node with '[' delimiter char anyway
                    argslatex += nodelist_to_latex([argn])
            elif argt == '{':
                # either a group node with '{' delimiter char, or single node argument
                argslatex += nodelist_to_latex([argn])
            else:
                raise ValueError("Unknown argument type: {!r}".format(argt))
        return argslatex

    latex = ''
    for n in nodelist:
        if n is None:
            continue
        if n.isNodeType(LatexCharsNode):
            latex += n.chars
            continue

        if n.isNodeType(LatexMacroNode):
            latex += r'\%s%s%s' %(n.macroname, n.macro_post_space, add_args(n.nodeargd))
            continue

        if n.isNodeType(LatexSpecialsNode):
            latex += r'%s%s' %(n.specials_chars, add_args(n.nodeargd))
            continue
        
        if n.isNodeType(LatexCommentNode):
            latex += '%'+n.comment+n.comment_post_space
            continue
        
        if n.isNodeType(LatexGroupNode):
            latex += n.delimiters[0] + nodelist_to_latex(n.nodelist) + n.delimiters[1]
            continue
        
        if n.isNodeType(LatexEnvironmentNode):
            latex += r'\begin{%s}%s' %(n.envname, add_args(n.nodeargd))
            latex += nodelist_to_latex(n.nodelist)
            latex += r'\end{%s}' %(n.envname)
            continue
        
        if n.isNodeType(LatexMathNode):
            latex += n.delimiters[0] + nodelist_to_latex(n.nodelist) + n.delimiters[1]
            continue
        
        latex += "<[UNKNOWN LATEX NODE: \'%s\']>"%(n.nodeType().__name__)

    return latex
    



def put_in_braces(brace_char, thestring):
    # DON'T USE. WILL BE REMOVED IN FUTURE VERSION.
    if (brace_char == '{'):
        return '{%s}' %(thestring)
    if (brace_char == '['):
        return '[%s]' %(thestring)
    if (brace_char == '('):
        return '(%s)' %(thestring)
    if (brace_char == '<'):
        return '<%s>' %(thestring)

    return brace_char + thestring + brace_char



def disp_node(n, indent=0, context='* ', skip_group=False):
    # Don't rely upon this function.
    title = ''
    comment = ''
    iterchildren = []

    def add_args():
        if n.nodeargd is None:
            #iterchildren.append(('<no args>', '', None))
            return
        elif n.nodeargd.argspec is None or n.nodeargd.argnlist is None:
            iterchildren.append(('<args> ', '<cannot be displayed>', None))
            return
        for argt, argn in zip(n.nodeargd.argspec, n.nodeargd.argnlist):
            if argt == '[':
                t = '[.]: '
            elif argt == '{':
                t = '{.}: '
            elif argt == '*':
                t = '<*>:   '
            else:
                t = '<unknown>: '
            iterchildren.append((t, [argn], False))

    if n is None:
        title = '<None>'
    elif n.isNodeType(LatexCharsNode):
        title = repr(n.chars)
    elif n.isNodeType(LatexMacroNode):
        title = '\\'+n.macroname
        add_args()
    elif n.isNodeType(LatexSpecialsNode):
        title = n.specials_chars + ' (specials)'
        add_args()
    elif n.isNodeType(LatexCommentNode):
        title = '%' + n.comment.strip()
    elif n.isNodeType(LatexGroupNode):
        if (skip_group):
            for nn in n.arg:
                disp_node(nn, indent=indent, context=context)
            return
        title = 'Group: '
        iterchildren.append(('* ', n.nodelist, False))
    elif n.isNodeType(LatexEnvironmentNode):
        title = '\\begin{%s}' %(n.environmentname)
        add_args()
        iterchildren.append(('* ', n.nodelist, False))
    elif n.isNodeType(LatexMathNode):
        title = n.delimiters[0]+n.displaytype+' math'+n.delimiters[1]
        iterchildren.append(('* ', n.nodelist, False))
    else:
        print("UNKNOWN NODE TYPE: %s"%(n.nodeType().__name__))

    print(' '*indent + context + title + '  '+comment)

    for context, nodelist, skip in iterchildren:
        if isinstance(nodelist, _basestring):
            print(' '*(indent+4) + context + nodelist)
            continue
        for nn in nodelist:
            disp_node(nn, indent=indent+4, context=context, skip_group=skip)




def make_json_encoder(latexwalker, use_line_numbers=True):

    class LatexNodesJSONEncoder(json.JSONEncoder):
        # not official API for now
        """
        A :py:class:`json.JSONEncoder` that can encode :py:class:`LatexNode` objects
        (and subclasses).
        """

        def __init__(self, *args, **kwargs):
            super(LatexNodesJSONEncoder, self).__init__(*args, **kwargs)

        def default(self, obj):
            if isinstance(obj, LatexNode):
                # Prepare a dictionary with the correct keys and values.
                n = obj
                d = {
                    'nodetype': n.__class__.__name__,
                }
                #redundant_fields = getattr(n, '_redundant_fields', n._fields)
                for fld in n._fields:
                    d[fld] = n.__dict__[fld]
                d.update(latexwalker.pos_to_lineno_colno(n.pos, as_dict=True))
                return d

            if isinstance(obj, macrospec.ParsedMacroArgs):
                return obj.to_json_object()

            # else:
            return super(LatexNodesJSONEncoder, self).default(obj)

    
    return LatexNodesJSONEncoder
