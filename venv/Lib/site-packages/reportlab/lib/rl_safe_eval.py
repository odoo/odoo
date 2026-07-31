#this code is copied/stolen/borrowed/modified from various sources including
#https://github.com/zopefoundation/AccessControl
#https://github.com/zopefoundation/RestrictedPython
#https://github.com/danthedeckie/simpleeval
#hopefully we are standing on giants' shoulders
import sys, os, ast, re, weakref, time, copy, math
eval_debug = int(os.environ.get('EVAL_DEBUG','0'))
strTypes = (bytes,str)
isPy39 = sys.version_info[:2]>=(3,9)

haveNameConstant = hasattr(ast,'NameConstant')
import textwrap

class BadCode(ValueError):
	pass

# For AugAssign the operator must be converted to a string.
augOps = {
	ast.Add: '+=',
	ast.Sub: '-=',
	ast.Mult: '*=',
	ast.Div: '/=',
	ast.Mod: '%=',
	ast.Pow: '**=',
	ast.LShift: '<<=',
	ast.RShift: '>>=',
	ast.BitOr: '|=',
	ast.BitXor: '^=',
	ast.BitAnd: '&=',
	ast.FloorDiv: '//=',
	ast.MatMult: '@=',
}

# For creation allowed magic method names. See also
# https://docs.python.org/3/reference/datamodel.html#special-method-names
__allowed_magic_methods__ = frozenset([
	'__init__',
	'__contains__',
	'__lt__',
	'__le__',
	'__eq__',
	'__ne__',
	'__gt__',
	'__ge__',
	])

__rl_unsafe__ = frozenset('''builtins breakpoint __annotations__ co_argcount co_cellvars co_code co_consts
						__code__ co_filename co_firstlineno co_flags co_freevars co_kwonlyargcount
						co_lnotab co_name co_names co_nlocals co_posonlyargcount co_stacksize
						co_varnames cr_await cr_code cr_frame cr_origin cr_running __defaults__
						f_back f_builtins f_code f_exc_traceback f_exc_type f_exc_value f_globals
						f_lasti f_lineno f_locals f_restricted f_trace __func__ func_code func_defaults
						func_doc func_globals func_name gi_code gi_frame gi_running gi_yieldfrom
						__globals__ im_class im_func im_self __iter__ __kwdefaults__ __module__
						__name__ next __qualname__ __self__ tb_frame tb_lasti tb_lineno tb_next
						globals vars locals'''.split()
						)
__rl_unsafe_re__ = re.compile(r'\b(?:%s)' % '|'.join(__rl_unsafe__),re.M)


def copy_locations(new_node, old_node):
	ast.copy_location(new_node, old_node)
	ast.fix_missing_locations(new_node)

class UntrustedAstTransformer(ast.NodeTransformer):

	def __init__(self, names_seen=None, nameIsAllowed=None):
		super(UntrustedAstTransformer, self).__init__()
		self.names_seen = {} if names_seen is None else names_seen
		self.nameIsAllowed = nameIsAllowed

		# Global counter to construct temporary variable names.
		self._tmp_idx = 0
		self._tmp_pfx = '_tmp%s' % repr(time.time()).replace('.','')

	@property
	def tmpName(self):
		name = '%s%s' % (self._tmp_pfx,self._tmp_idx)
		self._tmp_idx += 1
		return name

	def error(self, node, msg):
		raise BadCode('Line %s: %s' %  (getattr(node, 'lineno', '??'), msg))

	def guard_iter(self, node):
		"""
		Converts:
			for x in expr
		to
			for x in __rl_getiter__(expr)

		Also used for
		* list comprehensions
		* dict comprehensions
		* set comprehensions
		* generator expresions
		"""
		node = self.visit_children(node)

		if isinstance(node.target, ast.Tuple):
			spec = self.gen_unpack_spec(node.target)
			new_iter = ast.Call(
				func=ast.Name('__rl_iter_unpack_sequence__', ast.Load()),
				args=[node.iter, spec, ast.Name('__rl_getiter__', ast.Load())],
				keywords=[])
		else:
			new_iter = ast.Call(
				func=ast.Name('__rl_getiter__', ast.Load()),
				args=[node.iter],
				keywords=[])

		copy_locations(new_iter, node.iter)
		node.iter = new_iter
		return node

	def is_starred(self, ob):
		return isinstance(ob, ast.Starred)

	def gen_unpack_spec(self, tpl):
		"""Generate a specification for '__rl_unpack_sequence__'.

		This spec is used to protect sequence unpacking.
		The primary goal of this spec is to tell which elements in a sequence
		are sequences again. These 'child' sequences have to be protected
		again.

		For example there is a sequence like this:
			(a, (b, c), (d, (e, f))) = g

		On a higher level the spec says:
			- There is a sequence of len 3
			- The element at index 1 is a sequence again with len 2
			- The element at index 2 is a sequence again with len 2
			  - The element at index 1 in this subsequence is a sequence again
				with len 2

		With this spec '__rl_unpack_sequence__' does something like this for
		protection (len checks are omitted):

			t = list(__rl_getiter__(g))
			t[1] = list(__rl_getiter__(t[1]))
			t[2] = list(__rl_getiter__(t[2]))
			t[2][1] = list(__rl_getiter__(t[2][1]))
			return t

		The 'real' spec for the case above is then:
			spec = {
				'min_len': 3,
				'childs': (
					(1, {'min_len': 2, 'childs': ()}),
					(2, {
							'min_len': 2,
							'childs': (
								(1, {'min_len': 2, 'childs': ()})
							)
						}
					)
				)
			}

		So finally the assignment above is converted into:
			(a, (b, c), (d, (e, f))) = __rl_unpack_sequence__(g, spec)
		"""
		spec = ast.Dict(keys=[], values=[])

		spec.keys.append(ast.Str('childs'))
		spec.values.append(ast.Tuple([], ast.Load()))

		# starred elements in a sequence do not contribute into the min_len.
		# For example a, b, *c = g
		# g must have at least 2 elements, not 3. 'c' is empyt if g has only 2.
		min_len = len([ob for ob in tpl.elts if not self.is_starred(ob)])
		offset = 0

		for idx, val in enumerate(tpl.elts):
			# After a starred element specify the child index from the back.
			# Since it is unknown how many elements from the sequence are
			# consumed by the starred element.
			# For example a, *b, (c, d) = g
			# Then (c, d) has the index '-1'
			if self.is_starred(val):
				offset = min_len + 1

			elif isinstance(val, ast.Tuple):
				el = ast.Tuple([], ast.Load())
				el.elts.append(ast.Num(idx - offset))
				el.elts.append(self.gen_unpack_spec(val))
				spec.values[0].elts.append(el)

		spec.keys.append(ast.Str('min_len'))
		spec.values.append(ast.Num(min_len))

		return spec

	def protect_unpack_sequence(self, target, value):
		spec = self.gen_unpack_spec(target)
		return ast.Call(
			func=ast.Name('__rl_unpack_sequence__', ast.Load()),
			args=[value, spec, ast.Name('__rl_getiter__', ast.Load())],
			keywords=[])

	def gen_unpack_wrapper(self, node, target, ctx='store'):
		"""Helper function to protect tuple unpacks.

		node: used to copy the locations for the new nodes.
		target: is the tuple which must be protected.
		ctx: Defines the context of the returned temporary node.

		It returns a tuple with two element.

		Element 1: Is a temporary name node which must be used to
				   replace the target.
				   The context (store, param) is defined
				   by the 'ctx' parameter..

		Element 2: Is a try .. finally where the body performs the
				   protected tuple unpack of the temporary variable
				   into the original target.
		"""

		# Generate a tmp name to replace the tuple with.
		tnam = self.tmpName

		# Generates an expressions which protects the unpack.
		# converter looks like 'wrapper(tnam)'.
		# 'wrapper' takes care to protect sequence unpacking with __rl_getiter__.
		converter = self.protect_unpack_sequence(
			target,
			ast.Name(tnam, ast.Load()))

		# Assign the expression to the original names.
		# Cleanup the temporary variable.
		# Generates:
		# try:
		#	  # converter is 'wrapper(tnam)'
		#	  arg = converter
		# finally:
		#	  del tmp_arg
		try_body = [ast.Assign(targets=[target], value=converter)]
		finalbody = [self.gen_del_stmt(tnam)]

		cleanup = ast.Try(
			body=try_body, finalbody=finalbody, handlers=[], orelse=[])

		if ctx == 'store':
			ctx = ast.Store()
		elif ctx == 'param':
			ctx = ast.Param()
		else:  # pragma: no cover
			# Only store and param are defined ctx.
			raise NotImplementedError('bad ctx "%s"' % type(ctx))

		# This node is used to catch the tuple in a tmp variable.
		tmp_target = ast.Name(tnam, ctx)

		copy_locations(tmp_target, node)
		copy_locations(cleanup, node)

		return (tmp_target, cleanup)

	def gen_none_node(self):
		return ast.NameConstant(value=None) if hasNameConstant else ast.Name(id='None', ctx=ast.Load())

	def gen_lambda(self, args, body):
		return ast.Lambda(
			args=ast.arguments(
				args=args, vararg=None, kwarg=None, defaults=[]),
			body=body)

	def gen_del_stmt(self, name_to_del):
		return ast.Delete(targets=[ast.Name(name_to_del, ast.Del())])

	def transform_slice(self, slice_):
		"""Transform slices into function parameters.

		ast.Slice nodes are only allowed within a ast.Subscript node.
		To use a slice as an argument of ast.Call it has to be converted.
		Conversion is done by calling the 'slice' function from builtins
		"""

		if isinstance(slice_, ast.Index):
			return slice_.value

		elif isinstance(slice_, ast.Slice):
			# Create a python slice object.
			args = []

			if slice_.lower:
				args.append(slice_.lower)
			else:
				args.append(self.gen_none_node())

			if slice_.upper:
				args.append(slice_.upper)
			else:
				args.append(self.gen_none_node())

			if slice_.step:
				args.append(slice_.step)
			else:
				args.append(self.gen_none_node())

			return ast.Call(
				func=ast.Name('slice', ast.Load()),
				args=args,
				keywords=[])

		elif isinstance(slice_, ast.ExtSlice):
			dims = ast.Tuple([], ast.Load())
			for item in slice_.dims:
				dims.elts.append(self.transform_slice(item))
			return dims

		elif isPy39:
			return slice_

		else:  # pragma: no cover
			# Index, Slice and ExtSlice are only defined Slice types.
			raise NotImplementedError("Unknown slice type: %s" % slice_)

	def isAllowedName(self, node, name):
		if name is None: return
		self.nameIsAllowed(name)

	def check_function_argument_names(self, node):
		# In python3 arguments are always identifiers.
		# In python2 the 'Python.asdl' specifies expressions, but
		# the python grammer allows only identifiers or a tuple of
		# identifiers. If its a tuple 'tuple parameter unpacking' is used,
		# which is gone in python3.
		# See https://www.python.org/dev/peps/pep-3113/

		for arg in node.args.args:
			self.isAllowedName(node, arg.arg)

		if node.args.vararg:
			self.isAllowedName(node, node.args.vararg.arg)

		if node.args.kwarg:
			self.isAllowedName(node, node.args.kwarg.arg)

		for arg in node.args.kwonlyargs:
			self.isAllowedName(node, arg.arg)

	def check_import_names(self, node):
		"""Check the names being imported.

		This is a protection against rebinding dunder names like
		__rl_getitem__,__rl_set__ via imports.

		=> 'from _a import x' is ok, because '_a' is not added to the scope.
		"""
		for name in node.names:
			if '*' in name.name:
				self.error(node, '"*" imports are not allowed.')
			self.isAllowedName(node, name.name)
			if name.asname:
				self.isAllowedName(node, name.asname)

		return self.visit_children(node)

	def gen_attr_check(self, node, attr_name):
		"""Check if 'attr_name' is allowed on the object in node.

		It generates (_getattr_(node, attr_name) and node).
		"""

		call_getattr = ast.Call(
			func=ast.Name('__rl_getattr__', ast.Load()),
			args=[node, ast.Str(attr_name)],
			keywords=[])

		return ast.BoolOp(op=ast.And(), values=[call_getattr, node])

	def visit_Constant(self, node):
		"""Allow constant literals with restriction for Ellipsis.

		Constant replaces Num, Str, Bytes, NameConstant and Ellipsis in
		Python 3.8+.
		:see: https://docs.python.org/dev/whatsnew/3.8.html#deprecated
		"""
		if node.value is Ellipsis:
			# Deny using `...`.
			# Special handling necessary as ``self.not_allowed(node)``
			# would return the Error Message:
			# 'Constant statements are not allowed.'
			# which is only partial true.
			self.error(node, 'Ellipsis statements are not allowed.')
			return
		return self.visit_children(node)

	# ast for Variables
	def visit_Name(self, node):
		node = self.visit_children(node)

		if isinstance(node.ctx, ast.Load):
			if node.id == 'print':
				self.error(node,'print function is not allowed')
			self.names_seen[node.id] = True

		self.isAllowedName(node, node.id)
		return node

	def visit_Call(self, node):
		"""Checks calls with '*args' and '**kwargs'.

		Note: The following happens only if '*args' or '**kwargs' is used.

		Transfroms 'foo(<all the possible ways of args>)' into
		__rl_apply__(foo, <all the possible ways for args>)

		The thing is that '__rl_apply__' has only '*args', '**kwargs', so it gets
		Python to collapse all the myriad ways to call functions
		into one manageable from.

		From there, '__rl_apply__()' wraps args and kws in guarded accessors,
		then calls the function, returning the value.
		"""

		if isinstance(node.func, ast.Name):
			if node.func.id == 'exec':
				self.error(node, 'Exec calls are not allowed.')
			elif node.func.id == 'eval':
				self.error(node, 'Eval calls are not allowed.')

		needs_wrap = False

		for pos_arg in node.args:
			if isinstance(pos_arg, ast.Starred):
				needs_wrap = True

		for keyword_arg in node.keywords:
			if keyword_arg.arg is None:
				needs_wrap = True

		node = self.visit_children(node)

		#if not needs_wrap:
		#	return node

		node.args.insert(0, node.func)
		node.func = ast.Name('__rl_apply__', ast.Load())
		copy_locations(node.func, node.args[0])
		return node

	def visit_Attribute(self, node):
		"""Checks and mutates attribute access/assignment.

		'a.b' becomes '__rl_getattr__(a, "b")'
		"""
		if node.attr.startswith('__') and node.attr != '__':
			self.error(node, '"%s" is an invalid attribute'%node.attr)

		if isinstance(node.ctx, ast.Load):
			node = self.visit_children(node)
			new_node = ast.Call(
				func=ast.Name('__rl_getattr__', ast.Load()),
				args=[node.value, ast.Str(node.attr)],
				keywords=[])

			copy_locations(new_node, node)
			return new_node

		elif isinstance(node.ctx, (ast.Store, ast.Del)):
			node = self.visit_children(node)
			new_value = ast.Call(
				func=ast.Name('__rl_sd__', ast.Load()),
				args=[node.value],
				keywords=[])

			copy_locations(new_value, node.value)
			node.value = new_value
			return node

		else:  # pragma: no cover
			# Impossible Case only ctx Load, Store and Del are defined in ast.
			raise NotImplementedError("Unknown ctx type: %s" % type(node.ctx))

	# Subscripting
	def visit_Subscript(self, node):
		"""Transforms all kinds of subscripts.

		'v[a]' becomes '__rl_getitem__(foo, a)'
		'v[:b]' becomes '__rl_getitem__(foo, slice(None, b, None))'
		'v[a:]' becomes '__rl_getitem__(foo, slice(a, None, None))'
		'v[a:b]' becomes '__rl_getitem__(foo, slice(a, b, None))'
		'v[a:b:c]' becomes '__rl_getitem__(foo, slice(a, b, c))'
		'v[a,b:c] becomes '__rl_getitem__(foo, (a, slice(b, c, None)))'
		#'v[a] = c' becomes '_rl_write__(v)[a] = c'
		#'del v[a]' becomes 'del __rl_sd__(v)[a]'
		"""
		node = self.visit_children(node)

		# 'AugStore' and 'AugLoad' are defined in 'Python.asdl' as possible
		# 'expr_context'. However, according to Python/ast.c
		# they are NOT used by the implementation => No need to worry here.
		# Instead ast.c creates 'AugAssign' nodes, which can be visit_ed.

		if isinstance(node.ctx, ast.Load):
			new_node = ast.Call(
				func=ast.Name('__rl_getitem__', ast.Load()),
				args=[node.value, self.transform_slice(node.slice)],
				keywords=[])

			copy_locations(new_node, node)
			return new_node

		elif isinstance(node.ctx, (ast.Del, ast.Store)):
			#new_value = ast.Call(
			#	func=ast.Name('__rl_sd__', ast.Load()),
			#	args=[node.value],
			#	keywords=[])

			#copy_locations(new_value, node)
			#node.value = new_value
			return node

		else:  # pragma: no cover
			# Impossible Case only ctx Load, Store and Del are defined in ast.
			raise NotImplementedError("Unknown ctx type: %s" % type(node.ctx))

	# Statements
	def visit_Assign(self, node):
		node = self.visit_children(node)

		if not any(isinstance(t, ast.Tuple) for t in node.targets):
			return node

		# Handle sequence unpacking.
		# For briefness this example omits cleanup of the temporary variables.
		# Check 'transform_tuple_assign' how its done.
		#
		# - Single target (with nested support)
		# (a, (b, (c, d))) = <exp>
		# is converted to
		# (a, t1) = __rl_getiter__(<exp>)
		# (b, t2) = __rl_getiter__(t1)
		# (c, d) = __rl_getiter__(t2)
		#
		# - Multi targets
		# (a, b) = (c, d) = <exp>
		# is converted to
		# (c, d) = __rl_getiter__(<exp>)
		# (a, b) = __rl_getiter__(<exp>)
		# Why is this valid ? The original bytecode for this multi targets
		# behaves the same way.

		# ast.NodeTransformer works with list results.
		# He injects it at the rightplace of the node's parent statements.
		new_nodes = []

		# python fills the right most target first.
		for target in reversed(node.targets):
			if isinstance(target, ast.Tuple):
				wrapper = ast.Assign(
					targets=[target],
					value=self.protect_unpack_sequence(target, node.value))
				new_nodes.append(wrapper)
			else:
				new_node = ast.Assign(targets=[target], value=node.value)
				new_nodes.append(new_node)

		for new_node in new_nodes:
			copy_locations(new_node, node)

		return new_nodes

	def visit_AugAssign(self, node):
		"""Forbid certain kinds of AugAssign

		According to the language reference (and ast.c) the following nodes
		are are possible:
		Name, Attribute, Subscript

		Note that although augmented assignment of attributes and
		subscripts is disallowed, augmented assignment of names (such
		as 'n += 1') is allowed.
		'n += 1' becomes 'n = __rl_augAssign__("+=", n, 1)'
		"""

		node = self.visit_children(node)

		if isinstance(node.target, ast.Attribute):
			self.error(node, "Augmented assignment of attributes is not allowed.")

		elif isinstance(node.target, ast.Subscript):
			self.error(node, "Augmented assignment of object items and slices is not allowed.")

		elif isinstance(node.target, ast.Name):
			new_node = ast.Assign(
				targets=[node.target],
				value=ast.Call(
					func=ast.Name('__rl_augAssign__', ast.Load()),
					args=[
						ast.Str(augOps[type(node.op)]),
						ast.Name(node.target.id, ast.Load()),
						node.value
						],
					keywords=[]))

			copy_locations(new_node, node)
			return new_node
		else:  # pragma: no cover
			# Impossible Case - Only Node Types:
			# * Name
			# * Attribute
			# * Subscript
			# defined, those are checked before.
			raise NotImplementedError("Unknown target type: %s" % type(node.target))

	def visit_While(node):
		self.visit_children(node)
		return node

	def visit_ExceptHandler(self, node):
		"""Protect tuple unpacking on exception handlers.

		try:
			.....
		except Exception as (a, b):
			....

		becomes

		try:
			.....
		except Exception as tmp:
			try:
				(a, b) = __rl_getiter__(tmp)
			finally:
				del tmp
		"""
		node = self.visit_children(node)

		self.isAllowedName(node, node.name)
		return node

	def visit_With(self, node):
		"""Protect tuple unpacking on with statements."""
		node = self.visit_children(node)

		items = node.items

		for item in reversed(items):
			if isinstance(item.optional_vars, ast.Tuple):
				tmp_target, unpack = self.gen_unpack_wrapper(
					node,
					item.optional_vars)

				item.optional_vars = tmp_target
				node.body.insert(0, unpack)

		return node

	# Function and class definitions
	def visit_FunctionDef(self, node):
		"""Allow function definitions (`def`) with some restrictions."""
		self.isAllowedName(node, node.name)
		self.check_function_argument_names(node)

		return node

	def visit_Lambda(self, node):
		"""Allow lambda with some restrictions."""
		self.check_function_argument_names(node)

		node = self.visit_children(node)

		return node

	def visit_ClassDef(self, node):
		"""Check the name of a class definition."""
		self.isAllowedName(node, node.name)
		node = self.visit_children(node)
		if any(keyword.arg == 'metaclass' for keyword in node.keywords):
			self.error(node, 'The keyword argument "metaclass" is not allowed.')
		CLASS_DEF = textwrap.dedent('''\
			class %s(metaclass=__metaclass__):
				pass
		''' % node.name)
		new_class_node = ast.parse(CLASS_DEF).body[0]
		new_class_node.body = node.body
		new_class_node.bases = node.bases
		new_class_node.decorator_list = node.decorator_list
		return new_class_node

	# Imports
	def visit_Import(self, node):
		return self.check_import_names(node)

		node = self.visit_children(node)
		new_node = ast.Call(
						func=ast.Name('__rl_add__', ast.Load()),
							args=[node.left, node.right],
							keywords=[])
		copy_locations(new_node, node)
		return new_node

	def visit_BinOp(self,node):
		node = self.visit_children(node)
		op = node.op
		if isinstance(op,(ast.Mult,ast.Add,ast.Pow)):
			opf = ('__rl_mult__' if isinstance(op,ast.Mult)
					else '__rl_add__' if isinstance(op,ast.Add)
					else '__rl_pow__')
			new_node = ast.Call(
						func=ast.Name(opf, ast.Load()),
							args=[node.left, node.right],
							keywords=[])
			copy_locations(new_node, node)
			return new_node
		return node

	visit_ImportFrom = visit_Import
	visit_For = guard_iter
	visit_comprehension = guard_iter

	def generic_visit(self, node):
		"""Reject nodes which do not have a corresponding `visit` method."""
		self.not_allowed(node)

	def not_allowed(self, node):
		self.error(node, '%s statements are not allowed.'%node.__class__.__name__)

	def visit_children(self, node):
		"""Visit the contents of a node."""
		return super(UntrustedAstTransformer, self).generic_visit(node)

	if eval_debug>=2:
		def visit(self, node):
			method = 'visit_' + node.__class__.__name__
			visitor = getattr(self, method, self.generic_visit)
			print('visitor=%s=%r node=%r' % (method,visitor,node))
			return visitor(node)

	visit_Ellipsis = not_allowed
	visit_MatMult = not_allowed
	visit_Exec = not_allowed
	visit_Nonlocal = not_allowed
	visit_AsyncFunctionDef = not_allowed
	visit_Await = not_allowed
	visit_AsyncFor = not_allowed
	visit_AsyncWith = not_allowed
	visit_Print = not_allowed

	visit_Num = visit_children
	visit_Str = visit_children
	visit_Bytes = visit_children
	visit_List = visit_children
	visit_Tuple = visit_children
	visit_Set = visit_children
	visit_Dict = visit_children
	visit_FormattedValue = visit_children
	visit_JoinedStr = visit_children
	visit_NameConstant = visit_children
	visit_Load = visit_children
	visit_Store = visit_children
	visit_Del = visit_children
	visit_Starred = visit_children
	visit_Expression = visit_children
	visit_Expr = visit_children
	visit_UnaryOp = visit_children
	visit_UAdd = visit_children
	visit_USub = visit_children
	visit_Not = visit_children
	visit_Invert = visit_children
	visit_Add = visit_children
	visit_Sub = visit_children
	visit_Mult = visit_children
	visit_Div = visit_children
	visit_FloorDiv = visit_children
	visit_Pow = visit_children
	visit_Mod = visit_children
	visit_LShift = visit_children
	visit_RShift = visit_children
	visit_BitOr = visit_children
	visit_BitXor = visit_children
	visit_BitAnd = visit_children
	visit_BoolOp = visit_children
	visit_And = visit_children
	visit_Or = visit_children
	visit_Compare = visit_children
	visit_Eq = visit_children
	visit_NotEq = visit_children
	visit_Lt = visit_children
	visit_LtE = visit_children
	visit_Gt = visit_children
	visit_GtE = visit_children
	visit_Is = visit_children
	visit_IsNot = visit_children
	visit_In = visit_children
	visit_NotIn = visit_children
	visit_keyword = visit_children
	visit_IfExp = visit_children
	visit_Index = visit_children
	visit_Slice = visit_children
	visit_ExtSlice = visit_children
	visit_ListComp = visit_children
	visit_SetComp = visit_children
	visit_GeneratorExp = visit_children
	visit_DictComp = visit_children
	visit_Raise = visit_children
	visit_Assert = visit_children
	visit_Delete = visit_children
	visit_Pass = visit_children
	visit_alias = visit_children
	visit_If = visit_children
	visit_Break = visit_children
	visit_Continue = visit_children
	visit_Try = visit_children
	visit_TryFinally = visit_children
	visit_TryExcept = visit_children
	visit_withitem = visit_children
	visit_arguments = visit_children
	visit_arg = visit_children
	visit_Return = visit_children
	visit_Yield = visit_children
	visit_YieldFrom = visit_children
	visit_Global = visit_children
	visit_Module = visit_children
	visit_Param = visit_children

def astFormat(node):
	return ast.dump(copy.deepcopy(node),annotate_fields=True, include_attributes=True,indent=4)

class __rl_SafeIter__:
	def __init__(self, it, owner):
		self.__rl_iter__ = owner().__rl_real_iter__(it)
		self.__rl_owner__ = owner

	def __iter__(self):
		return self

	def __next__(self):
		self.__rl_owner__().__rl_check__()
		return	next(self.__rl_iter__)

	next = __next__  # Python 2 compat

__rl_safe_builtins__ = {}	#constructed below
def safer_globals(g=None):
	if g is None:
		g = sys._getframe(1).f_globals.copy()
	for name in ('__annotations__', '__doc__', '__loader__', '__name__', '__package__', '__spec__'):
		if name in g:
			del g[name]
		g['__builtins__'] = __rl_safe_builtins__.copy()
	return g

math_log10 = math.log10
__rl_undef__ = object()
class __RL_SAFE_ENV__:
	__time_time__ = time.time
	__weakref_ref__ = weakref.ref
	__slicetype__ = type(slice(0))
	def __init__(self, timeout=None, allowed_magic_methods=None):
		self.timeout = timeout if timeout is not None else self.__rl_tmax__
		self.allowed_magic_methods = (__allowed_magic_methods__ if allowed_magic_methods==True
									else allowed_magic_methods) if allowed_magic_methods else []
		import builtins
		self.__rl_gen_range__ = builtins.range

		self.__rl_real_iter__ = builtins.iter

		class __rl_dict__(dict):
			def __new__(cls, *args,**kwds):
				if len(args)==1 and not isinstance(args[0],dict):
					try:
						it = self.__real_iter__(args[0])
					except TypeError:
						pass
					else:
						args = (self.__rl_getiter__(it),)
				return dict.__new__(cls,*args,**kwds)

		class __rl_missing_func__:
			def __init__(self,name):
				self.__name__ = name
			def __call__(self,*args,**kwds):
				raise BadCode('missing global %s' % self.__name__)

		self.real_bi = builtins
		self.bi_replace = (
				('open',__rl_missing_func__('open')),
				('iter',self.__rl_getiter__),
				)

		__rl_safe_builtins__.update({_:getattr(builtins,_) for _ in 
			('''None False True abs bool callable chr complex divmod float hash hex id int
		isinstance issubclass len oct ord range repr round slice str tuple setattr
		classmethod staticmethod property divmod next object getattr dict iter pow list
		type max min sum enumerate zip hasattr filter map any all sorted reversed range
		set frozenset

		ArithmeticError AssertionError AttributeError BaseException BufferError BytesWarning
		DeprecationWarning EOFError EnvironmentError Exception FloatingPointError FutureWarning
		GeneratorExit IOError ImportError ImportWarning IndentationError IndexError KeyError
		KeyboardInterrupt LookupError MemoryError NameError NotImplementedError OSError
		OverflowError PendingDeprecationWarning ReferenceError RuntimeError RuntimeWarning
		StopIteration SyntaxError SyntaxWarning SystemError SystemExit TabError TypeError
		UnboundLocalError UnicodeDecodeError UnicodeEncodeError UnicodeError UnicodeTranslateError
		UnicodeWarning UserWarning ValueError Warning ZeroDivisionError
		__build_class__'''
				).split()})

		self.__rl_builtins__ = __rl_builtins__ = {_:__rl_missing_func__(_) for _ in dir(builtins) if callable(getattr(builtins,_))}
		__rl_builtins__.update(__rl_safe_builtins__)

		#these are used in the tree visitor
		__rl_builtins__['__rl_add__'] = self.__rl_add__
		__rl_builtins__['__rl_mult__'] = self.__rl_mult__
		__rl_builtins__['__rl_pow__'] = self.__rl_pow__
		__rl_builtins__['__rl_sd__'] = self.__rl_sd__
		__rl_builtins__['__rl_augAssign__'] = self.__rl_augAssign__
		__rl_builtins__['__rl_getitem__'] = self.__rl_getitem__
		__rl_builtins__['__rl_getattr__'] = self.__rl_getattr__
		__rl_builtins__['__rl_getiter__'] = self.__rl_getiter__
		__rl_builtins__['__rl_max_len__'] = self.__rl_max_len__
		__rl_builtins__['__rl_max_pow_digits__'] = self.__rl_max_pow_digits__
		__rl_builtins__['__rl_iter_unpack_sequence__'] = self.__rl_iter_unpack_sequence__
		__rl_builtins__['__rl_unpack_sequence__'] = self.__rl_unpack_sequence__
		__rl_builtins__['__rl_apply__'] = lambda func,*args,**kwds: self.__rl_apply__(func,args,kwds)
		__rl_builtins__['__rl_SafeIter__'] = __rl_SafeIter__

		#these are tested builtins
		__rl_builtins__['getattr'] = self.__rl_getattr__
		__rl_builtins__['dict'] = __rl_dict__
		__rl_builtins__['iter'] = self.__rl_getiter__
		__rl_builtins__['pow'] = self.__rl_pow__
		__rl_builtins__['list'] = self.__rl_list__
		__rl_builtins__['type'] = self.__rl_type__
		__rl_builtins__['max'] = self.__rl_max__
		__rl_builtins__['min'] = self.__rl_min__
		__rl_builtins__['sum'] = self.__rl_sum__
		__rl_builtins__['enumerate'] = self.__rl_enumerate__
		__rl_builtins__['zip'] = self.__rl_zip__
		__rl_builtins__['hasattr'] = self.__rl_hasattr__
		__rl_builtins__['filter'] = self.__rl_filter__
		__rl_builtins__['map'] = self.__rl_map__
		__rl_builtins__['any'] = self.__rl_any__
		__rl_builtins__['all'] = self.__rl_all__
		__rl_builtins__['sorted'] = self.__rl_sorted__
		__rl_builtins__['reversed'] = self.__rl_reversed__
		__rl_builtins__['range'] = self.__rl_range__
		__rl_builtins__['set'] = self.__rl_set__
		__rl_builtins__['frozenset'] = self.__rl_frozenset__

	def __rl_type__(self,*args):
		if len(args)==1: return type(*args)
		raise BadCode('type call error')

	def __rl_check__(self):
		if self.__time_time__() >= self.__rl_limit__:
			raise BadCode('Resources exceeded')

	def __rl_sd__(self,obj):
		return obj

	def __rl_getiter__(self,it):
		return __rl_SafeIter__(it,owner=self.__weakref_ref__(self))

	def __rl_max__(self,arg,*args,**kwds):
		if args:
			arg = [arg]
			arg.extend(args)
		return max(self.__rl_args_iter__(arg),**kwds)

	def __rl_min__(self,arg,*args,**kwds):
		if args:
			arg = [arg]
			arg.extend(args)
		return min(self.__rl_args_iter__(arg),**kwds)

	def __rl_sum__(self, sequence, start=0):
		return sum(self.__rl_args_iter__(sequence), start)

	def __rl_enumerate__(self, seq):
		return enumerate(self.__rl_args_iter__(seq))

	def __rl_zip__(self,*args):
		return zip(*[self.__rl_args_iter__(self.__rl_getitem__(args, i)) for i in range(len(args))])

	def __rl_hasattr__(self, obj, name):
		try:
			self.__rl_getattr__(obj, name)
		except (AttributeError, BadCode, TypeError):
			return False
		return True

	def __rl_filter__(self, f, seq):
		return filter(f,self.__rl_args_iter__(seq))

	def __rl_map__(self, f, seq):
		return map(f,self.__rl_args_iter__(seq))

	def __rl_any__(self, seq):
		return any(self.__rl_args_iter__(seq))

	def __rl_all__(self, seq):
		return all(self.__rl_args_iter__(seq))

	def __rl_sorted__(self, seq, **kwds):
		return sorted(self.__rl_args_iter__(seq),**kwds)

	def __rl_reversed__(self, seq):
		return self.__rl_args_iter__(reversed(seq))

	def __rl_range__(self,start,*args):
		return self.__rl_getiter__(range(start,*args))

	def __rl_set__(self, it):
		return set(self.__rl_args_iter__(it))

	def __rl_frozenset__(self, it):
		return frozenset(self.__rl_args_iter__(it))

	def __rl_iter_unpack_sequence__(self, it, spec, _getiter_):
		"""Protect sequence unpacking of targets in a 'for loop'.

		The target of a for loop could be a sequence.
		For example "for a, b in it"
		=> Each object from the iterator needs guarded sequence unpacking.
		"""
		# The iteration itself needs to be protected as well.
		for ob in _getiter_(it):
			yield self.__rl_unpack_sequence__(ob, spec, _getiter_)

	def __rl_unpack_sequence__(self, it, spec, _getiter_):
		"""Protect nested sequence unpacking.

		Protect the unpacking of 'it' by wrapping it with '_getiter_'.
		Furthermore for each child element, defined by spec,
		__rl_unpack_sequence__ is called again.

		Have a look at transformer.py 'gen_unpack_spec' for a more detailed
		explanation.
		"""
		# Do the guarded unpacking of the sequence.
		ret = list(self.__rl__getiter__(it))

		# If the sequence is shorter then expected the interpreter will raise
		# 'ValueError: need more than X value to unpack' anyway
		# => No childs are unpacked => nothing to protect.
		if len(ret) < spec['min_len']:
			return ret

		# For all child elements do the guarded unpacking again.
		for (idx, child_spec) in spec['childs']:
			ret[idx] = self.__rl_unpack_sequence__(ret[idx], child_spec, _getiter_)
		return ret

	def __rl_is_allowed_name__(self, name):
		"""Check names if they are allowed.
		If ``allow_magic_methods is True`` names in `__allowed_magic_methods__`
		are additionally allowed although their names start with `_`.
		"""
		if isinstance(name,strTypes):
			if name in __rl_unsafe__ or (name.startswith('__')
				and name!='__'
				and name not in self.allowed_magic_methods):
				raise BadCode('unsafe access of %s' % name)

	def __rl_getattr__(self, obj, a, *args):
		if isinstance(obj, strTypes) and a=='format':
			raise BadCode('%s.format is not implemented' % type(obj))
		self.__rl_is_allowed_name__(a)
		return getattr(obj,a,*args)

	def __rl_getitem__(self, obj, a):
		if type(a) is self.__slicetype__:
			if a.step is not None:
				v = obj[a]
			else:
				start = a.start
				stop = a.stop
				if start is None:
					start = 0
				if stop is None:
					v = obj[start:]
				else:
					v = obj[start:stop]
			return v
		elif isinstance(a,strTypes):
			self.__rl_is_allowed_name__(a)
			return obj[a]
		return obj[a]

	__rl_tmax__ = 5
	__rl_max_len__ = 100000
	__rl_max_pow_digits__ = 100

	def __rl_add__(self, a, b):
		if (hasattr(a, '__len__') and hasattr(b, '__len__')
				and (len(a) + len(b)) > self.__rl_max_len__):
			raise BadCode("excessive length")
		return a + b

	def __rl_mult__(self, a, b):
		if ((hasattr(a, '__len__') and b * len(a) > self.__rl_max_len__)
				or (hasattr(b, '__len__') and a * len(b) > self.__rl_max_len__)):
			raise BadCode("excessive length")
		return a * b

	def __rl_pow__(self, a, b):
		try:
			if b>0:
				if int(b*math_log10(a)+1)>self.__rl_max_pow_digits__:
					raise BadCode
		except:
			raise BadCode('%r**%r invalid or too large' % (a,b))
		return a ** b

	def __rl_augAssign__(self,op,v,i):
		if op=='+=': return self.__rl_add__(v,i)
		if op=='-=': return v-i
		if op=='*=': return self.__rl_mult__(v,i)
		if op=='/=': return v/i
		if op=='%=': return v%i
		if op=='**=': return self.__rl_pow__(v,i)
		if op=='<<=': return v<<i
		if op=='>>=': return v>>i
		if op=='|=': return v|i
		if op=='^=': return v^i
		if op=='&=': return v&i
		if op=='//=': return v//i

	def __rl_apply__(self, func, args, kwds):
		obj = getattr(func,'__self__',None)
		if obj:
			if isinstance(obj,dict) and func.__name__ in ('pop','setdefault','get', 'popitem'):
				self.__rl_is_allowed_name__(args[0])
		return func(*[a for a in self.__rl_getiter__(args)], **{k:v for k,v in kwds.items()})

	def __rl_args_iter__(self,*args):
		if len(args) == 1:
			i = args[0]
			# Don't double-wrap
			if isinstance(i, __rl_SafeIter__):
				return i
			if not isinstance(i,self.__rl_gen_range__):
				return self.__rl_getiter__(i)
		return self.__rl_getiter__(iter(*args))

	def __rl_list__(self,it):
		return list(self.__rl_getiter__(it))

	def __rl_compile__(self, src, fname='<string>', mode="eval", flags=0, inherit=True, visit=None):
		names_seen = {}
		if not visit:
			bcode = compile(src, fname, mode=mode, flags=flags, dont_inherit=not inherit)
		else:
			astc = ast.parse(src, fname, mode)
			if eval_debug>0:
				print('pre:\n%s\n'%astFormat(astc))
			astc = visit(astc)
			if eval_debug>0:
				print('post:\n%s\n'%astFormat(astc))
			bcode = compile(astc, fname, mode=mode)
		return bcode, names_seen

	def __rl_safe_eval__(self, expr, g, l, mode, timeout=None, allowed_magic_methods=None, __frame_depth__=3):
		bcode, ns = self.__rl_compile__(expr, fname='<string>', mode=mode, flags=0, inherit=True,
				visit=UntrustedAstTransformer(nameIsAllowed=self.__rl_is_allowed_name__).visit)
		if None in (l,g):
			G = sys._getframe(__frame_depth__)
			L = G.f_locals.copy() if l is None else l
			G = G.f_globals.copy() if g is None else g
		else:
			G = g
			L = l
		obi = (G['__builtins__'],) if '__builtins__' in G else False
		G['__builtins__'] = self.__rl_builtins__
		self.__rl_limit__ = self.__time_time__() + (timeout if timeout is not None else self.timeout)
		if allowed_magic_methods is not None:
			self.allowed_magic_methods = ( __allowed_magic_methods__ if allowed_magic_methods==True
										else allowed_magic_methods) if allowed_magic_methods else []
		sbi = [].append
		bi = self.real_bi
		bir = self.bi_replace
		for n, r in bir:
			sbi(getattr(bi,n))
			setattr(bi,n,r)
		try:
			return eval(bcode,G,L)
		finally:
			sbi = sbi.__self__
			for i, (n, r) in enumerate(bir):
				setattr(bi,n,sbi[i])
			if obi:
				G['__builtins__'] = obi[0]

class __rl_safe_eval__:
	'''creates one environment and re-uses it'''
	mode = 'eval'
	def __init__(self):
		self.env = None

	def __call__(self, expr, g=None, l=None, timeout=None, allowed_magic_methods=None):
		if not self.env: self.env = __RL_SAFE_ENV__(timeout=timeout, allowed_magic_methods=allowed_magic_methods)
		return self.env.__rl_safe_eval__(expr, g, l, self.mode, timeout=timeout,
			allowed_magic_methods=allowed_magic_methods,
			__frame_depth__=2)

class __rl_safe_exec__(__rl_safe_eval__):
	mode = 'exec'

rl_safe_exec = __rl_safe_exec__()
rl_safe_eval = __rl_safe_eval__()
