from __future__ import division
import re, json

##### Parsing utilities #####

def split_delimited(delimiters, split_by, text):
    """
    Generator that walks the ``text`` and splits it into an array on
    ``split_by``, being careful not to break inside a delimiter pair.
    ``delimiters`` should be an even-length string with each pair of matching
    delimiters listed together, open first.


    >>> list(split_delimited('{}[]', ',', ''))
    ['']
    >>> list(split_delimited('', ',', 'foo,bar'))
    ['foo', 'bar']
    >>> list(split_delimited('[]', ',', 'foo,[bar, baz]'))
    ['foo', '[bar, baz]']
    >>> list(split_delimited('{}', ' ', '{Type Name} name Desc'))
    ['{Type Name}', 'name', 'Desc']
    >>> list(split_delimited('[]{}', ',', '[{foo,[bar, baz]}]'))
    ['[{foo,[bar, baz]}]']

    Two adjacent delimiters result in a zero-length string between them:

    >>> list(split_delimited('{}', ' ', '{Type Name}  Desc'))
    ['{Type Name}', '', 'Desc']

    ``split_by`` may be a predicate function instead of a string, in which
    case it should return true on a character to split.

    >>> list(split_delimited('', lambda c: c in '[]{}, ', '[{foo,[bar, baz]}]'))
    ['', '', 'foo', '', 'bar', '', 'baz', '', '', '']

    """
    delims = [0] * (len(delimiters) // 2)
    actions = {}
    for i in range(0, len(delimiters), 2):
        actions[delimiters[i]] = (i // 2, 1)
        actions[delimiters[i + 1]] = (i // 2, -1)

    if isinstance(split_by, str):
        def split_fn(c):
            return c == split_by
    else:
        split_fn = split_by
    last = 0

    for i in range(len(text)):
        c = text[i]
        if split_fn(c) and not any(delims):
            yield text[last:i]
            last = i + 1
        try:
            which, dir = actions[c]
            delims[which] = delims[which] + dir
        except KeyError:
            pass  # Normal character
    yield text[last:]


def strip_stars(doc_comment):
    r"""
    Strip leading stars from a doc comment.

    >>> strip_stars('/** This is a comment. */')
    'This is a comment.'
    >>> strip_stars('/**\n * This is a\n * multiline comment. */')
    'This is a\n multiline comment.'
    >>> strip_stars('/** \n\t * This is a\n\t * multiline comment. \n*/')
    'This is a\n multiline comment.'

    """
    return re.sub('\n\s*?\*\s*?', '\n', doc_comment[3:-2]).strip()


def split_tag(section):
    """
    Split the JSDoc tag text (everything following the @) at the first
    whitespace.  Returns a tuple of (tagname, body).
    """
    splitval = re.split('\s+', section, 1)
    tag, body = len(splitval) > 1 and splitval or (splitval[0], '')
    return tag.strip(), body.strip()


FUNCTION_REGEXPS = [
    'function (\w+)',
    '(\w+):\sfunction',
    '\.(\w+)\s*=\s*function',
]


def guess_function_name(next_line, regexps=FUNCTION_REGEXPS):
    """
    Attempt to determine the function name from the first code line
    following the comment.  The patterns recognized are described by
    `regexps`, which defaults to FUNCTION_REGEXPS.  If a match is successful,
    returns the function name.  Otherwise, returns None.
    """
    for regexp in regexps:
        match = re.search(regexp, next_line)
        if match:
            return match.group(1)
    return None


def guess_parameters(next_line):
    """
    Attempt to guess parameters based on the presence of a parenthesized
    group of identifiers.  If successful, returns a list of parameter names;
    otherwise, returns None.
    """
    match = re.search('\(([\w\s,]+)\)', next_line)
    if match:
        return [arg.strip() for arg in match.group(1).split(',')]
    else:
        return None


def parse_comment(doc_comment, next_line):
    r"""
    Split the raw comment text into a dictionary of tags.  The main comment
    body is included as 'doc'.

    >>> comment = get_doc_comments(read_file('examples/module.js'))[4][0]
    >>> parse_comment(strip_stars(comment), '')['doc']
    'This is the documentation for the fourth function.\n\n Since the function being documented is itself generated from another\n function, its name needs to be specified explicitly. using the @function tag'
    >>> parse_comment(strip_stars(comment), '')['function']
    'not_auto_discovered'

    If there are multiple tags with the same name, they're included as a list:

    >>> parse_comment(strip_stars(comment), '')['param']
    ['{String} arg1 The first argument.', '{Int} arg2 The second argument.']

    """
    sections = re.split('\n\s*@', doc_comment)
    tags = {
        'doc': sections[0].strip(),
        'guessed_function': guess_function_name(next_line),
        'guessed_params': guess_parameters(next_line)
    }
    for section in sections[1:]:
        tag, body = split_tag(section)
        if tag in tags:
            existing = tags[tag]
            try:
                existing.append(body)
            except AttributeError:
                tags[tag] = [existing, body]
        else:
            tags[tag] = body
    return tags


#### Classes #####

class CommentDoc(object):
    """
    Base class for all classes that represent a parsed comment of some sort.
    """

    def __init__(self, parsed_comment):
        self.parsed = parsed_comment

    def __str__(self):
        return "Docs for " + self.name

    def __repr__(self):
        return str(self)

    def __contains__(self, tag_name):
        return tag_name in self.parsed

    def __getitem__(self, tag_name):
        return self.get(tag_name)

    def get(self, tag_name, default=''):
        """
        Return the value of a particular tag, or None if that tag doesn't
        exist.  Use 'doc' for the comment body itself.
        """
        return self.parsed.get(tag_name, default)

    def get_as_list(self, tag_name):
        """
        Return the value of a tag, making sure that it's a list.  Absent
        tags are returned as an empty-list; single tags are returned as a
        one-element list.

        The returned list is a copy, and modifications do not affect the
        original object.
        """
        val = self.get(tag_name, [])
        if isinstance(val, list):
            return val[:]
        else:
            return [val]

    @property
    def doc(self):
        """
        Return the comment body.
        """
        return self.get('doc')

    @property
    def url(self):
        """
        Return a URL for the comment, within the page.
        """
        return '#' + self.name

    @property
    def see(self):
        """
        Return a list of all @see tags on the comment.
        """
        return self.get_as_list('see')

    def to_json(self):
        """
        Return a JSON representation of the CommentDoc.  Keys are as per
        to_dict.
        """
        return json.dumps(self.to_dict())

    def to_dict(self):
        """
        Return a dictionary representation of the CommentDoc.  The keys of
        this correspond to the tags in the comment, with the comment body in
        `doc`.
        """
        return self.parsed.copy()

class ParamDoc(object):
    """
    Represents a parameter, option, or parameter-like object, basically
    anything that has a name, a type, and a description, separated by spaces.
    This is also used for return types and exceptions, which use an empty
    string for the name.

    >>> param = ParamDoc('{Array<DOM>} elems The elements to act upon')
    >>> param.name
    'elems'
    >>> param.doc
    'The elements to act upon'
    >>> param.type
    'Array<DOM>'

    You can also omit the type: if the first element is not surrounded by
    curly braces, it's assumed to be the name instead:

    >>> param2 = ParamDoc('param1 The first param')
    >>> param2.type
    ''
    >>> param2.name
    'param1'
    >>> param2.doc
    'The first param'

    """

    def __init__(self, text):
        parsed = list(split_delimited('{}', ' ', text))
        if parsed[0].startswith('{') and parsed[0].endswith('}'):
            self.type = parsed[0][1:-1]
            self.name = parsed[1]
            self.doc = ' '.join(parsed[2:])
        else:
            self.type = ''
            self.name = parsed[0]
            self.doc = ' '.join(parsed[1:])

    def to_dict(self):
        """
        Convert this to a dict.  Keys (all strings) are:

            - **name**: Parameter name
            - **type**: Parameter type
            - **doc**: Parameter description
        """
        return {
            'name': self.name,
            'type': self.type,
            'doc': self.doc
        }

    def to_html(self, css_class=''):
        """
        Returns the parameter as a dt/dd pair.
        """
        if self.name and self.type:
            header_text = '%s (%s)' % (self.name, self.type)
        elif self.type:
            header_text = self.type
        else:
            header_text = self.name
        return '<dt>%s</dt><dd>%s</dd>' % (header_text, self.doc)


##### DEPENDENCIES #####

class CyclicDependency(Exception):
    """
    Exception raised if there is a cyclic dependency.
    """

    def __init__(self, remaining_dependencies):
        self.values = remaining_dependencies

    def __str__(self):
        return ('The following dependencies result in a cycle: '
                + ', '.join(self.values))


class MissingDependency(Exception):
    """
    Exception raised if a file references a dependency that doesn't exist.
    """

    def __init__(self, file, dependency):
        self.file = file
        self.dependency = dependency

    def __str__(self):
        return "Couldn't find dependency %s when processing %s" % \
               (self.dependency, self.file)


def build_dependency_graph(start_nodes, js_doc):
    """
    Build a graph where nodes are filenames and edges are reverse dependencies
    (so an edge from jquery.js to jquery.dimensions.js indicates that jquery.js
    must be included before jquery.dimensions.js).  The graph is represented
    as a dictionary from filename to (in-degree, edges) pair, for ease of
    topological sorting.  Also returns a list of nodes of degree zero.
    """
    queue = []
    dependencies = {}
    start_sort = []

    def add_vertex(file):
        in_degree = len(js_doc[file].module.dependencies)
        dependencies[file] = [in_degree, []]
        queue.append(file)
        if in_degree == 0:
            start_sort.append(file)

    def add_edge(from_file, to_file):
        dependencies[from_file][1].append(to_file)

    def is_in_graph(file):
        return file in dependencies

    for file in start_nodes:
        add_vertex(file)
    for file in queue:
        for dependency in js_doc[file].module.dependencies:
            if dependency not in js_doc:
                raise MissingDependency(file, dependency)
            if not is_in_graph(dependency):
                add_vertex(dependency)
            add_edge(dependency, file)
    return dependencies, start_sort


def topological_sort(dependencies, start_nodes):
    """
    Perform a topological sort on the dependency graph `dependencies`, starting
    from list `start_nodes`.
    """
    retval = []

    def edges(node):
        return dependencies[node][1]

    def in_degree(node):
        return dependencies[node][0]

    def remove_incoming(node):
        dependencies[node][0] = in_degree(node) - 1

    while start_nodes:
        node = start_nodes.pop()
        retval.append(node)
        for child in edges(node):
            remove_incoming(child)
            if not in_degree(child):
                start_nodes.append(child)
    leftover_nodes = [node for node in dependencies.keys()
                      if in_degree(node) > 0]
    if leftover_nodes:
        raise CyclicDependency(leftover_nodes)
    else:
        return retval


def find_dependencies(start_nodes, js_doc):
    """
    Sort the dependency graph, taking in a list of starting module names and a
    CodeBaseDoc (or equivalent dictionary).  Returns an ordered list of
    transitive dependencies such that no module appears before its
    dependencies.
    """
    return topological_sort(*build_dependency_graph(start_nodes, js_doc))
