"""gettext message extraction via Babel: http://babel.edgewall.org/"""
from StringIO import StringIO

from babel.messages.extract import extract_python

from mako import lexer, parsetree

def extract(fileobj, keywords, comment_tags, options):
    """Extract messages from Mako templates.

    :param fileobj: the file-like object the messages should be extracted from
    :param keywords: a list of keywords (i.e. function names) that should be
                     recognized as translation functions
    :param comment_tags: a list of translator tags to search for and include
                         in the results
    :param options: a dictionary of additional options (optional)
    :return: an iterator over ``(lineno, funcname, message, comments)`` tuples
    :rtype: ``iterator``
    """
    encoding = options.get('input_encoding', options.get('encoding', None))

    template_node = lexer.Lexer(fileobj.read(),
                                input_encoding=encoding).parse()
    for extracted in extract_nodes(template_node.get_children(),
                                        keywords, comment_tags, options):
        yield extracted

def extract_nodes(nodes, keywords, comment_tags, options):
    """Extract messages from Mako's lexer node objects

    :param nodes: an iterable of Mako parsetree.Node objects to extract from
    :param keywords: a list of keywords (i.e. function names) that should be
                     recognized as translation functions
    :param comment_tags: a list of translator tags to search for and include
                         in the results
    :param options: a dictionary of additional options (optional)
    :return: an iterator over ``(lineno, funcname, message, comments)`` tuples
    :rtype: ``iterator``
    """
    translator_comments = []
    in_translator_comments = False

    for node in nodes:
        child_nodes = None
        if in_translator_comments and isinstance(node, parsetree.Text) and \
                not node.content.strip():
            # Ignore whitespace within translator comments
            continue

        if isinstance(node, parsetree.Comment):
            value = node.text.strip()
            if in_translator_comments:
                translator_comments.extend(_split_comment(node.lineno, value))
                continue
            for comment_tag in comment_tags:
                if value.startswith(comment_tag):
                    in_translator_comments = True
                    translator_comments.extend(_split_comment(node.lineno,
                                                              value))
            continue

        if isinstance(node, parsetree.DefTag):
            code = node.function_decl.code
            child_nodes = node.nodes
        elif isinstance(node, parsetree.CallTag):
            code = node.code.code
            child_nodes = node.nodes
        elif isinstance(node, parsetree.PageTag):
            code = node.body_decl.code
        elif isinstance(node, parsetree.ControlLine):
            if node.isend:
                translator_comments = []
                in_translator_comments = False
                continue
            code = node.text
        elif isinstance(node, parsetree.Code):
            # <% and <%! blocks would provide their own translator comments
            translator_comments = []
            in_translator_comments = False

            code = node.code.code
        elif isinstance(node, parsetree.Expression):
            code = node.code.code
        else:
            translator_comments = []
            in_translator_comments = False
            continue

        # Comments don't apply unless they immediately preceed the message
        if translator_comments and \
                translator_comments[-1][0] < node.lineno - 1:
            translator_comments = []
        else:
            translator_comments = \
                [comment[1] for comment in translator_comments]

        if isinstance(code, unicode):
            code = code.encode('ascii', 'backslashreplace')
        code = StringIO(code)
        for lineno, funcname, messages, python_translator_comments \
                in extract_python(code, keywords, comment_tags, options):
            yield (node.lineno + (lineno - 1), funcname, messages,
                   translator_comments + python_translator_comments)

        translator_comments = []
        in_translator_comments = False

        if child_nodes:
            for extracted in extract_nodes(child_nodes, keywords, comment_tags,
                                           options):
                yield extracted


def _split_comment(lineno, comment):
    """Return the multiline comment at lineno split into a list of comment line
    numbers and the accompanying comment line"""
    return [(lineno + index, line) for index, line in
            enumerate(comment.splitlines())]
