from docutils import nodes, utils
from docutils.parsers.rst import Directive

from pygments.lexers import get_lexer_by_name, PythonLexer
PythonLexer.name = 'Python 2'

def setup(app):
    app.add_directive('switcher', SwitcherDirective)
    app.add_directive('case', CaseDirective)

class SwitcherDirective(Directive):
    has_content = True

    def run(self):
        self.assert_has_content()

        body = nodes.compound('\n'.join(self.content), classes=['tabs'])
        self.state.nested_parse(self.content, self.content_offset, body)

        titles = []
        for child in body.children:
            if isinstance(child, nodes.literal_block):
                titles.append(get_lexer_by_name(child['language']).name)
            else:
                assert child['names'], ("A switcher case must be either a "\
                                        "code block or a compound with a name")
                titles.append(' '.join(child['names']))
        tabs = nodes.bullet_list('', *[
            nodes.list_item('', nodes.Text(title))
            for title in titles
        ])
        node = nodes.compound('', tabs, body, classes=['content-switcher'])
        return [node]

class CaseDirective(Directive):
    required_arguments = 1
    final_argument_whitespace = True
    has_content = True

    def run(self):
        self.assert_has_content()

        node = nodes.compound('\n'.join(self.content), names=[self.arguments[0]])
        self.state.nested_parse(self.content, self.content_offset, node)
        return [node]
