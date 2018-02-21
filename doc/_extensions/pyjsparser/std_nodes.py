from .pyjsparserdata import *


class BaseNode:
    def finish(self):
        pass

    def finishArrayExpression(self, elements):
        self.type = Syntax.ArrayExpression
        self.elements = elements
        self.finish()
        return self

    def finishArrayPattern(self, elements):
        self.type = Syntax.ArrayPattern
        self.elements = elements
        self.finish()
        return self

    def finishArrowFunctionExpression(self, params, defaults, body, expression):
        self.type = Syntax.ArrowFunctionExpression
        self.id = None
        self.params = params
        self.defaults = defaults
        self.body = body
        self.generator = False
        self.expression = expression
        self.finish()
        return self

    def finishAssignmentExpression(self, operator, left, right):
        self.type = Syntax.AssignmentExpression
        self.operator = operator
        self.left = left
        self.right = right
        self.finish()
        return self

    def finishAssignmentPattern(self, left, right):
        self.type = Syntax.AssignmentPattern
        self.left = left
        self.right = right
        self.finish()
        return self

    def finishBinaryExpression(self, operator, left, right):
        self.type = Syntax.LogicalExpression if (operator == '||' or operator == '&&') else Syntax.BinaryExpression
        self.operator = operator
        self.left = left
        self.right = right
        self.finish()
        return self

    def finishBlockStatement(self, body):
        self.type = Syntax.BlockStatement
        self.body = body
        self.finish()
        return self

    def finishBreakStatement(self, label):
        self.type = Syntax.BreakStatement
        self.label = label
        self.finish()
        return self

    def finishCallExpression(self, callee, args):
        self.type = Syntax.CallExpression
        self.callee = callee
        self.arguments = args
        self.finish()
        return self

    def finishCatchClause(self, param, body):
        self.type = Syntax.CatchClause
        self.param = param
        self.body = body
        self.finish()
        return self

    def finishClassBody(self, body):
        self.type = Syntax.ClassBody
        self.body = body
        self.finish()
        return self

    def finishClassDeclaration(self, id, superClass, body):
        self.type = Syntax.ClassDeclaration
        self.id = id
        self.superClass = superClass
        self.body = body
        self.finish()
        return self

    def finishClassExpression(self, id, superClass, body):
        self.type = Syntax.ClassExpression
        self.id = id
        self.superClass = superClass
        self.body = body
        self.finish()
        return self

    def finishConditionalExpression(self, test, consequent, alternate):
        self.type = Syntax.ConditionalExpression
        self.test = test
        self.consequent = consequent
        self.alternate = alternate
        self.finish()
        return self

    def finishContinueStatement(self, label):
        self.type = Syntax.ContinueStatement
        self.label = label
        self.finish()
        return self

    def finishDebuggerStatement(self, ):
        self.type = Syntax.DebuggerStatement
        self.finish()
        return self

    def finishDoWhileStatement(self, body, test):
        self.type = Syntax.DoWhileStatement
        self.body = body
        self.test = test
        self.finish()
        return self

    def finishEmptyStatement(self, ):
        self.type = Syntax.EmptyStatement
        self.finish()
        return self

    def finishExpressionStatement(self, expression):
        self.type = Syntax.ExpressionStatement
        self.expression = expression
        self.finish()
        return self

    def finishForStatement(self, init, test, update, body):
        self.type = Syntax.ForStatement
        self.init = init
        self.test = test
        self.update = update
        self.body = body
        self.finish()
        return self

    def finishForInStatement(self, left, right, body):
        self.type = Syntax.ForInStatement
        self.left = left
        self.right = right
        self.body = body
        self.each = False
        self.finish()
        return self

    def finishFunctionDeclaration(self, id, params, defaults, body):
        self.type = Syntax.FunctionDeclaration
        self.id = id
        self.params = params
        self.defaults = defaults
        self.body = body
        self.generator = False
        self.expression = False
        self.finish()
        return self

    def finishFunctionExpression(self, id, params, defaults, body):
        self.type = Syntax.FunctionExpression
        self.id = id
        self.params = params
        self.defaults = defaults
        self.body = body
        self.generator = False
        self.expression = False
        self.finish()
        return self

    def finishIdentifier(self, name):
        self.type = Syntax.Identifier
        self.name = name
        self.finish()
        return self

    def finishIfStatement(self, test, consequent, alternate):
        self.type = Syntax.IfStatement
        self.test = test
        self.consequent = consequent
        self.alternate = alternate
        self.finish()
        return self

    def finishLabeledStatement(self, label, body):
        self.type = Syntax.LabeledStatement
        self.label = label
        self.body = body
        self.finish()
        return self

    def finishLiteral(self, token):
        self.type = Syntax.Literal
        self.value = token['value']
        self.raw = None  # todo fix it?
        if token.get('regex'):
            self.regex = token['regex']
        self.finish()
        return self

    def finishMemberExpression(self, accessor, object, property):
        self.type = Syntax.MemberExpression
        self.computed = accessor == '['
        self.object = object
        self.property = property
        self.finish()
        return self

    def finishNewExpression(self, callee, args):
        self.type = Syntax.NewExpression
        self.callee = callee
        self.arguments = args
        self.finish()
        return self

    def finishObjectExpression(self, properties):
        self.type = Syntax.ObjectExpression
        self.properties = properties
        self.finish()
        return self

    def finishObjectPattern(self, properties):
        self.type = Syntax.ObjectPattern
        self.properties = properties
        self.finish()
        return self

    def finishPostfixExpression(self, operator, argument):
        self.type = Syntax.UpdateExpression
        self.operator = operator
        self.argument = argument
        self.prefix = False
        self.finish()
        return self

    def finishProgram(self, body):
        self.type = Syntax.Program
        self.body = body
        self.finish()
        return self

    def finishPyimport(self, imp):
        self.type = 'PyimportStatement'
        self.imp = imp
        self.finish()
        return self

    def finishProperty(self, kind, key, computed, value, method, shorthand):
        self.type = Syntax.Property
        self.key = key
        self.computed = computed
        self.value = value
        self.kind = kind
        self.method = method
        self.shorthand = shorthand
        self.finish()
        return self

    def finishRestElement(self, argument):
        self.type = Syntax.RestElement
        self.argument = argument
        self.finish()
        return self

    def finishReturnStatement(self, argument):
        self.type = Syntax.ReturnStatement
        self.argument = argument
        self.finish()
        return self

    def finishSequenceExpression(self, expressions):
        self.type = Syntax.SequenceExpression
        self.expressions = expressions
        self.finish()
        return self

    def finishSpreadElement(self, argument):
        self.type = Syntax.SpreadElement
        self.argument = argument
        self.finish()
        return self

    def finishSwitchCase(self, test, consequent):
        self.type = Syntax.SwitchCase
        self.test = test
        self.consequent = consequent
        self.finish()
        return self

    def finishSuper(self, ):
        self.type = Syntax.Super
        self.finish()
        return self

    def finishSwitchStatement(self, discriminant, cases):
        self.type = Syntax.SwitchStatement
        self.discriminant = discriminant
        self.cases = cases
        self.finish()
        return self

    def finishTaggedTemplateExpression(self, tag, quasi):
        self.type = Syntax.TaggedTemplateExpression
        self.tag = tag
        self.quasi = quasi
        self.finish()
        return self

    def finishTemplateElement(self, value, tail):
        self.type = Syntax.TemplateElement
        self.value = value
        self.tail = tail
        self.finish()
        return self

    def finishTemplateLiteral(self, quasis, expressions):
        self.type = Syntax.TemplateLiteral
        self.quasis = quasis
        self.expressions = expressions
        self.finish()
        return self

    def finishThisExpression(self, ):
        self.type = Syntax.ThisExpression
        self.finish()
        return self

    def finishThrowStatement(self, argument):
        self.type = Syntax.ThrowStatement
        self.argument = argument
        self.finish()
        return self

    def finishTryStatement(self, block, handler, finalizer):
        self.type = Syntax.TryStatement
        self.block = block
        self.guardedHandlers = []
        self.handlers = [handler] if handler else []
        self.handler = handler
        self.finalizer = finalizer
        self.finish()
        return self

    def finishUnaryExpression(self, operator, argument):
        self.type = Syntax.UpdateExpression if (operator == '++' or operator == '--') else Syntax.UnaryExpression
        self.operator = operator
        self.argument = argument
        self.prefix = True
        self.finish()
        return self

    def finishVariableDeclaration(self, declarations):
        self.type = Syntax.VariableDeclaration
        self.declarations = declarations
        self.kind = 'var'
        self.finish()
        return self

    def finishLexicalDeclaration(self, declarations, kind):
        self.type = Syntax.VariableDeclaration
        self.declarations = declarations
        self.kind = kind
        self.finish()
        return self

    def finishVariableDeclarator(self, id, init):
        self.type = Syntax.VariableDeclarator
        self.id = id
        self.init = init
        self.finish()
        return self

    def finishWhileStatement(self, test, body):
        self.type = Syntax.WhileStatement
        self.test = test
        self.body = body
        self.finish()
        return self

    def finishWithStatement(self, object, body):
        self.type = Syntax.WithStatement
        self.object = object
        self.body = body
        self.finish()
        return self

    def finishExportSpecifier(self, local, exported):
        self.type = Syntax.ExportSpecifier
        self.exported = exported or local
        self.local = local
        self.finish()
        return self

    def finishImportDefaultSpecifier(self, local):
        self.type = Syntax.ImportDefaultSpecifier
        self.local = local
        self.finish()
        return self

    def finishImportNamespaceSpecifier(self, local):
        self.type = Syntax.ImportNamespaceSpecifier
        self.local = local
        self.finish()
        return self

    def finishExportNamedDeclaration(self, declaration, specifiers, src):
        self.type = Syntax.ExportNamedDeclaration
        self.declaration = declaration
        self.specifiers = specifiers
        self.source = src
        self.finish()
        return self

    def finishExportDefaultDeclaration(self, declaration):
        self.type = Syntax.ExportDefaultDeclaration
        self.declaration = declaration
        self.finish()
        return self

    def finishExportAllDeclaration(self, src):
        self.type = Syntax.ExportAllDeclaration
        self.source = src
        self.finish()
        return self

    def finishImportSpecifier(self, local, imported):
        self.type = Syntax.ImportSpecifier
        self.local = local or imported
        self.imported = imported
        self.finish()
        return self

    def finishImportDeclaration(self, specifiers, src):
        self.type = Syntax.ImportDeclaration
        self.specifiers = specifiers
        self.source = src
        self.finish()
        return self

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)

class Node(BaseNode):
    pass


class WrappingNode(BaseNode):
    def __init__(self, startToken=None):
        pass


def node_to_dict(node):  # extremely important for translation speed
    if isinstance(node, list):
        return [node_to_dict(e) for e in node]
    elif isinstance(node, dict):
        return dict((k, node_to_dict(v)) for k, v in node.items())
    elif not isinstance(node, BaseNode):
        return node
    return dict((k, node_to_dict(v)) for k, v in node.__dict__.items())
