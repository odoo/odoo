from pyjsparser.pyjsparserdata import Syntax

_binary = lambda n: [n['left'], n['right']]
_function = lambda n: n['params'] + n['defaults'] + [n['body']]
# yields children in visitation order
_children = {
    Syntax.ArrayExpression: lambda n: n['elements'],
    Syntax.ArrayPattern: lambda n: n['elements'],
    Syntax.ArrowFunctionExpression: _function,
    Syntax.AssignmentExpression: _binary,
    Syntax.AssignmentPattern: _binary,
    Syntax.BinaryExpression: _binary,
    Syntax.BlockStatement: lambda n: n['body'],
    Syntax.BreakStatement: lambda n: [],
    Syntax.CallExpression: lambda n: [n['callee']] + n['arguments'],
    Syntax.CatchClause: lambda n: [n['param'], n['body']],
    Syntax.ClassBody: lambda n: [n['body']],
    Syntax.ClassDeclaration: lambda n: [n['superClass'], n['body']],
    Syntax.ClassExpression: lambda n: [n['superClass'], n['body']],
    Syntax.ConditionalExpression: lambda n: [n['test'], n['consequent'], n['alternate']],
    Syntax.ContinueStatement: lambda n: [],
    Syntax.DebuggerStatement: lambda n: [],
    Syntax.DoWhileStatement: lambda n: [n['body'], n['test']],
    Syntax.EmptyStatement: lambda n: [],
    Syntax.ExportAllDeclaration: lambda n: [n['source']],
    Syntax.ExportDefaultDeclaration: lambda n: [n['declaration']],
    Syntax.ExportNamedDeclaration: lambda n: ([n['declaration']] if n['declaration'] else n['specifiers']) + [n['source']],
    Syntax.ExportSpecifier: lambda n: [n['local'], n['exported']],
    Syntax.ExpressionStatement: lambda n: [n['expression']],
    Syntax.ForStatement: lambda n: [n['init'], n['test'], n['update'], n['body']],
    Syntax.ForInStatement: lambda n: [n['left'], n['right'], n['body']],
    Syntax.FunctionDeclaration: _function,
    Syntax.FunctionExpression: _function,
    Syntax.Identifier: lambda n: [],
    Syntax.IfStatement: lambda n: [n['test'], n['consequent'], n['alternate']],
    Syntax.ImportDeclaration: lambda n: n['specifiers'] + [n['source']],
    Syntax.ImportDefaultSpecifier: lambda n: [n['local']],
    Syntax.ImportNamespaceSpecifier: lambda n: [n['local']],
    Syntax.ImportSpecifier: lambda n: [n['local'], n['imported']],
    Syntax.LabeledStatement: lambda n: [n['body']],
    Syntax.Literal: lambda n: [],
    Syntax.LogicalExpression: _binary,
    Syntax.MemberExpression: lambda n: [n['object'], n['property']],
    #Syntax.MethodDefinition: lambda n: [],
    Syntax.NewExpression: lambda n: [n['callee']] + n['arguments'],
    Syntax.ObjectExpression: lambda n: n['properties'],
    Syntax.ObjectPattern: lambda n: n['properties'],
    Syntax.Program: lambda n: n['body'],
    Syntax.Property: lambda n: [n['key'], n['value']],
    Syntax.RestElement: lambda n: [n['argument']],
    Syntax.ReturnStatement: lambda n: [n['argument']],
    Syntax.SequenceExpression: lambda n: n['expressions'],
    Syntax.SpreadElement: lambda n: [n['argument']],
    Syntax.Super: lambda n: [],
    Syntax.SwitchCase: lambda n: [n['test'], n['consequent']],
    Syntax.SwitchStatement: lambda n: [n['discriminant']] + n['cases'],
    Syntax.TaggedTemplateExpression: lambda n: [n['tag'], n['quasi']],
    Syntax.TemplateElement: lambda n: [],
    Syntax.TemplateLiteral: lambda n: n['quasis'] + n['expressions'],
    Syntax.ThisExpression: lambda n: [],
    Syntax.ThrowStatement: lambda n: [n['argument']],
    Syntax.TryStatement: lambda n: [n['block'], n['handler'], n['finalizer']],
    Syntax.UnaryExpression: lambda n: [n['argument']],
    Syntax.UpdateExpression: lambda n: [n['argument']],
    Syntax.VariableDeclaration: lambda n: n['declarations'],
    Syntax.VariableDeclarator: lambda n: [n['id'], n['init']],
    Syntax.WhileStatement: lambda n: [n['test'], n['body']],
    Syntax.WithStatement: lambda n: [n['object'], n['body']],
}

SKIP = object()
class Visitor(object):
    """
    Generic visitor for the pyjsparser AST.

    Visitation is driven by the ``visit`` method, which iterates the tree in
    depth-first pre-order.

    For each node, calls ``enter_$NODETYPE``, visits the children then calls
    ``exit_$NODETYPE``. If the enter or exit methods are not present on the
    visitor, falls back on ``enter_generic`` and ``exit_generic``.

    Any ``enter_`` method can return ``SKIP`` to suppress both the traversal
    of the subtree *and* the call to the corresponding ``exit_`` method
    (whether generic or specific).

    For convenience, ``visit`` will return whatever is set as the visitor's
    ``result`` attribute, ``None`` by default.

    ``visit`` can be given multiple root nodes, and it can be called multiple
    times. The ``result`` attribute is cleared at each call but not between
    two roots of the same ``visit`` call.
    """
    def __init__(self):
        super(Visitor, self).__init__()
        self.result = None

    def enter_generic(self, node): pass
    def exit_generic(self, node): pass

    def visit(self, nodes):
        if isinstance(nodes, dict):
            nodes = [nodes]
        # if multiple nodes are passed in, we need to reverse the order in
        # order to traverse front-to-back rather than the other way around
        nodes = list(reversed(nodes))

        while nodes:
            node = nodes.pop()
            # should probably filter None descendants in _children...
            if node is None:
                continue
            node_type = node['type']
            if node_type == '_exit':
                node = node['node']
                getattr(self, 'exit_' + node['type'], self.exit_generic)(node)
                continue

            if getattr(self, 'enter_' + node_type, self.enter_generic)(node) is SKIP:
                continue

            nodes.append({'type': '_exit', 'node': node})
            nodes.extend(reversed(_children[node_type](node)))

        return self.result

