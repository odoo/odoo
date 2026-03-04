# -*- coding: utf-8 -*-
#
# The MIT License (MIT)
# 
# Copyright (c) 2019 Philippe Faist
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


# Internal module. Internal API may move, disappear or otherwise change at any
# time and without notice.



import sys


if sys.version_info.major > 2:
    # Py3
    def unicode(s): return s
    _basestring = str
    _str_from_unicode = lambda x: x
    _unicode_from_str = lambda x: x
else:
    # Py2
    _basestring = basestring
    _str_from_unicode = lambda x: unicode(x).encode('utf-8')
    _unicode_from_str = lambda x: x.decode('utf-8')




class ParsedMacroArgs(object):
    r"""
    Parsed representation of macro arguments.

    The base class provides a simple way of storing the arguments as a list of
    parsed nodes.

    This base class can be subclassed to store additional information and
    provide more advanced APIs to access macro arguments for certain categories
    of macros.

    Arguments:

      - `argnlist` is a list of latexwalker nodes that represent macro
        arguments.  If the macro arguments are too complicated to store in a
        list, leave this as `None`.  (But then code that uses the latexwalker
        must be aware of your own API to access the macro arguments.)

        The difference between `argnlist` and the legacy `nodeargs` is that all
        options, regardless of optional or mandatory, are stored in the list
        `argnlist` with possible `None`\ 's at places where optional arguments
        were not provided.  Previously, whether a first optional argument was
        included in `nodeoptarg` or `nodeargs` depended on how the macro
        specification was given.

      - `argspec` is a string or a list that describes how each corresponding
        argument in `argnlist` represents.  If the macro arguments are too
        complicated to store in a list, leave this as `None`.  For standard
        macros and parsed arguments this is a string with characters '*', '[',
        '{' describing an optional star argument, an optional
        square-bracket-delimited argument, and a mandatory argument.

    Attributes:

    .. py:attribute:: argnlist

       The list of latexwalker nodes that was provided to the constructor

    .. py:attribute:: argspec

       Argument type specification provided to the constructor

    .. py:attribute:: legacy_nodeoptarg_nodeargs

       A tuple `(nodeoptarg, nodeargs)` that should be exposed as properties in
       :py:class:`~pylatexenc.latexwalker.LatexMacroNode` to provide (as best as
       possible) compatibility with pylatexenc < 2.

       This is either `(<1st optional arg node>, <list of remaining args>)` if
       the first argument is optional and all remaining args are mandatory; or
       it is `(None, <list of args>)` for any other argument structure.
    """
    def __init__(self, argnlist=[], argspec='', **kwargs):
        super(ParsedMacroArgs, self).__init__(**kwargs)
        
        self.argnlist = argnlist
        self.argspec = argspec

        # for LatexMacroNode to provide some kind of compatibility with pylatexenc < 2
        self.legacy_nodeoptarg_nodeargs = \
            self._get_legacy_attribs(self.argspec, self.argnlist)

    def _get_legacy_attribs(self, argspec, argnlist):
        nskip = 0
        while argspec.startswith('*'):
            argspec = argspec[1:]
            nskip += 1
        if argspec[0:1] == '[' and all(x == '{' for x in argspec[1:]):
            return ( argnlist[nskip], argnlist[nskip+1:] )
        else:
            return (None, argnlist)

        
    def to_json_object(self):
        r"""
        Called when we export the node structure to JSON when running latexwalker in
        command-line.

        Return a representation of the current parsed arguments in an object,
        typically a dictionary, that can easily be exported to JSON.  The object
        may contain latex nodes and other parsed-argument objects, as we use a
        custom JSON encoder that understands these types.

        Subclasses may
        """

        return dict(
            argspec=self.argspec,
            argnlist=self.argnlist,
        )

    def __repr__(self):
        return "{}(argspec={!r}, argnlist={!r})".format(
            self.__class__.__name__, self.argspec, self.argnlist
        )



class MacroStandardArgsParser(object):
    r"""
    Parses the arguments to a LaTeX macro.

    This class parses a simple macro argument specification with a specified
    arrangement of optional and mandatory arguments.

    This class also serves as base class for more advanced argument parsers
    (e.g. for a ``\verb+...+`` macro argument parser).  In such cases,
    subclasses should attempt to provide the most suitable `argspec` (and
    `argnlist` for the corresponding :py:class:`ParsedMacroArgs`) for their use,
    if appropriate, or set them to `None`.

    Arguments:

      - `argspec`: must be a string in which each character corresponds to an
        argument.  The character '{' represents a mandatory argument (single
        token or LaTeX group) and the character '[' denotes an optional argument
        delimited by braces.  The character '\*' denotes a possible star char at
        that position in the argument list, a corresponding
        ``latexwalker.LatexCharsNode('*')`` (or `None` if no star) will be
        inserted in the argument node list.  For instance, the string '\*{[[{'
        would be suitable to specify the signature of the '\\newcommand' macro.

        Currently, the argspec string may only contain the characters '\*', '{'
        and '['.

        The `argspec` may also be `None`, which is the same as specifying an
        empty string.

      - `optional_arg_no_space`: If set to `True`, then an optional argument
        cannot have any whitespace between the preceeding tokens and the '['
        character.  Set this to `True` in cases such as for ``\\`` in AMS-math
        environments, where AMS apparently introduced a patch to prevent a
        bracket on a new line after ``\\`` from being interpreted as the
        optional argument to ``\\``.
    
      - `args_math_mode`: Either `None`, or a list of the same length as
        `argspec`.  If a list is given, then each item must be `True`, `False`,
        or `None`.  The corresponding argument (cf. `argspec`) is then
        respectively parsed in math mode (`True`), in text mode (`False`), or
        with the mode unchanged (`None`).  If `args_math_mode` is `None`, then
        all arguments are parsed in the same mode as the current mode.

      - additional unrecognized keyword arguments are passed on to superclasses
        in case of multiple inheritance

    Attributes:

    .. py:attribute:: argspec

       Argument type specification provided to the constructor.

    .. py:attribute:: optional_arg_no_space

       See the corresponding constructor argument.

    .. py:attribute:: args_math_mode

       See the corresponding constructor argument.
    """
    def __init__(self, argspec=None, optional_arg_no_space=False,
                 args_math_mode=None, **kwargs):
        super(MacroStandardArgsParser, self).__init__(**kwargs)
        self.argspec = argspec if argspec else ''
        self.optional_arg_no_space = optional_arg_no_space
        self.args_math_mode = args_math_mode
        # catch bugs, make sure that argspec is a string with only accepted chars
        if not isinstance(self.argspec, _basestring) or \
           not all(x in '*[{' for x in self.argspec):
            raise TypeError(
                "argspec must be a string containing chars '*', '[', '{{' only: {!r}"
                .format(self.argspec)
            )
        # non-documented attribute that makes us ignore any leading '*'.  We use
        # this to emulate pylatexenc 1.x behavior when using the MacrosDef()
        # function explicitly
        self._like_pylatexenc1x_ignore_leading_star = False

    def parse_args(self, w, pos, parsing_state=None):
        r"""
        Parse the arguments encountered at position `pos` in the
        :py:class:`~pylatexenc.latexwalker.LatexWalker` instance `w`.

        You may override this function to provide custom parsing of complicated
        macro arguments (say, ``\verb+...+``).  The method will be called by
        keyword arguments, so the argument names should not be altered.

        The argument `w` is the :py:class:`pylatexenc.latexwalker.LatexWalker`
        object that is currently parsing LaTeX code.  You can call methods like
        `w.get_goken()`, `w.get_latex_expression()` etc., to parse and read
        arguments.

        The argument `parsing_state` is the current parsing state in the
        :py:class:`~pylatexenc.latexwalker.LatexWalker` (e.g., are we currently
        in math mode?).  See doc for
        :py:class:`~pylatexenc.latexwalker.ParsingState`.

        This function should return a tuple `(argd, pos, len)` where:

        - `argd` is a :py:class:`ParsedMacroArgs` instance, or an instance of a
          subclass of :py:class:`ParsedMacroArgs`.  The base `parse_args()`
          provided here returns a :py:class:`ParsedMacroArgs` instance.

        - `pos` is the position of the first parsed content.  It should be the
          same as the `pos` argument, except if there is whitespace at that
          position in which case the returned `pos` would have to be the
          position where the argument contents start.

        - `len` is the length of the parsed expression.  You will probably want
          to continue parsing stuff at the index `pos+len` in the string.
        """

        from .. import latexwalker

        if parsing_state is None:
            parsing_state = w.make_parsing_state()

        argnlist = []

        if self.args_math_mode is not None and \
           len(self.args_math_mode) != len(self.argspec):
            raise ValueError("Invalid args_math_mode={!r} for argspec={!r}!"
                             .format(self.args_math_mode, self.argspec))

        def get_inner_parsing_state(j):
            if self.args_math_mode is None:
                return parsing_state
            amm = self.args_math_mode[j]
            if amm is None or amm == parsing_state.in_math_mode:
                return parsing_state
            if amm == True:
                return parsing_state.sub_context(in_math_mode=True)
            return parsing_state.sub_context(in_math_mode=False)

        p = pos

        if self._like_pylatexenc1x_ignore_leading_star:
            # ignore any leading '*' character
            tok = w.get_token(p)
            if tok.tok == 'char' and tok.arg == '*':
                p = tok.pos + tok.len

        for j, argt in enumerate(self.argspec):
            if argt == '{':
                (node, np, nl) = w.get_latex_expression(
                    p,
                    strict_braces=False,
                    parsing_state=get_inner_parsing_state(j)
                )
                p = np + nl
                argnlist.append(node)

            elif argt == '[':

                if self.optional_arg_no_space and p < len(w.s) and w.s[p].isspace():
                    # don't try to read optional arg, we don't allow space
                    argnlist.append(None)
                    continue

                optarginfotuple = w.get_latex_maybe_optional_arg(
                    p,
                    parsing_state=get_inner_parsing_state(j)
                )
                if optarginfotuple is None:
                    argnlist.append(None)
                    continue
                (node, np, nl) = optarginfotuple
                p = np + nl
                argnlist.append(node)

            elif argt == '*':
                # possible star.
                tok = w.get_token(p)
                if tok.tok == 'char' and tok.arg.startswith('*'):
                    # has star
                    argnlist.append(
                        w.make_node(latexwalker.LatexCharsNode,
                                    parsing_state=get_inner_parsing_state(j),
                                    chars='*', pos=tok.pos, len=1)
                    )
                    p = tok.pos + 1
                else:
                    argnlist.append(None)

            else:
                raise LatexWalkerError(
                    "Unknown macro argument kind for macro: {!r}".format(argt)
                )

        parsed = ParsedMacroArgs(
            argspec=self.argspec,
            argnlist=argnlist,
        )

        return (parsed, pos, p-pos)


    def __repr__(self):
        return '{}(argspec={!r}, optional_arg_no_space={!r}, args_math_mode={!r})'.format(
            self.__class__.__name__, self.argspec, self.optional_arg_no_space,
            self.args_math_mode
        )
    



class ParsedVerbatimArgs(ParsedMacroArgs):
    r"""
    Parsed representation of arguments to LaTeX verbatim constructs, such as
    ``\begin{verbatim}...\end{verbatim}`` or ``\verb|...|``.

    Instances of `ParsedVerbatimArgs` are returned by the args parser
    :py:class:`VerbatimArgsParser`.

    Arguments:

      - `verbatim_chars_node` --- a properly initialized
        :py:class:`pylatexenc.latexwalker.LatexCharsNode` that stores the
        verbatim text provided.  It is used to initialize the base class
        :py:class:`ParsedMacroArgs` to expose a single mandatory argument with
        the given verbatim text.  The `verbatim_text` attribute is initialized
        from this node, too.

      - `verbatim_delimiters` --- a 2-item tuple of characters used to delimit
        the verbatim arguemnt (in case of a ``\verb+...+`` macro) or `None`.

    Attributes:

    .. py:attribute:: verbatim_text

       The verbatim text that was provided

    .. py:attribute:: verbatim_delimiters

       If the verbatim text was specified as an argument to ``\verb$...$``, then
       this is set to a 2-item tuple that specifies the begin and end
       delimiters.  Otherwise, the attribute is `None`.
    """
    def __init__(self, verbatim_chars_node, verbatim_delimiters=None,
                 **kwargs):

        # provide argspec/argnlist to the parent class so that any code that is
        # not "verbatim environment-aware" sees this simply as the argument to
        # an empty verbatim environment
        super(ParsedVerbatimArgs, self).__init__(
            argspec='{',
            argnlist=[verbatim_chars_node],
            **kwargs
        )
        
        self.verbatim_text = verbatim_chars_node.chars
        self.verbatim_delimiters = verbatim_delimiters

    def __repr__(self):
        return "{}(verbatim_text={!r}, verbatim_delimiters={!r})".format(
            self.__class__.__name__, self.verbatim_text, self.verbatim_delimiters
        )



class VerbatimArgsParser(MacroStandardArgsParser):
    r"""
    Parses the arguments to various LaTeX "verbatim" constructs such as
    ``\begin{verbatim}...\end{verbatim}`` environment or ``\verb+...+``.

    This class also serves to illustrate how to write custom parsers for
    complicated macro arguments.  See also :py:class:`MacroStandardArgsParser`.

    Arguments:

    .. py:attribute:: verbatim_arg_type

      One of 'verbatim-environment' or 'verb-macro'.
    """
    def __init__(self, verbatim_arg_type, **kwargs):
        super(VerbatimArgsParser, self).__init__(argspec='{', **kwargs)
        self.verbatim_arg_type = verbatim_arg_type

    def parse_args(self, w, pos, parsing_state=None):

        from .. import latexwalker

        if self.verbatim_arg_type == 'verbatim-environment':
            # simply scan the string until we find '\end{verbatim}'.  That's
            # exactly how LaTeX processes it.
            endverbpos = w.s.find(r'\end{verbatim}', pos)
            if endverbpos == -1:
                raise latexwalker.LatexWalkerParseError(
                    s=w.s,
                    pos=pos,
                    msg=r"Cannot find matching \end{verbatim}"
                )
            # do NOT include the "\end{verbatim}", latexwalker will expect to
            # see it:
            len_ = endverbpos-pos

            argd = ParsedVerbatimArgs(
                verbatim_chars_node=w.make_node(latexwalker.LatexCharsNode,
                                                parsing_state=parsing_state,
                                                chars=w.s[pos:pos+len_],
                                                pos=pos,
                                                len=len_)
            )
            return (argd, pos, len_)

        if self.verbatim_arg_type == 'verb-macro':
            # read the next nonwhitespace char. This is the delimiter of the
            # argument
            while w.s[pos].isspace():
                pos += 1
                if pos >= len(w.s):
                    raise latexwalker.LatexWalkerParseError(
                        s=w.s,
                        pos=pos,
                        msg=r"Missing argument to \verb command"
                    )
            verbdelimchar = w.s[pos]
            beginpos = pos+1
            endpos = w.s.find(verbdelimchar, beginpos)
            if endpos == -1:
                raise latexwalker.LatexWalkerParseError(
                    s=w.s,
                    pos=pos,
                    msg=r"End of stream reached while reading argument to \verb command"
                )
            
            verbarg = w.s[beginpos:endpos]

            argd = ParsedVerbatimArgs(
                verbatim_chars_node=w.make_node(latexwalker.LatexCharsNode,
                                                parsing_state=parsing_state,
                                                chars=verbarg,
                                                pos=beginpos,
                                                len=endpos-beginpos),
                verbatim_delimiters=(verbdelimchar, verbdelimchar),
            )

            return (argd, pos, endpos+1-pos) # include delimiters in pos/len


    def __repr__(self):
        return '{}(verbatim_arg_type={!r})'.format(
            self.__class__.__name__, self.verbatim_arg_type
        )

