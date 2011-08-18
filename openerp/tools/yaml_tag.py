import yaml
import logging

class YamlTag(object):
    """
    Superclass for constructors of custom tags defined in yaml file.
    __str__ is overriden in subclass and used for serialization in module recorder.
    """
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def __getitem__(self, key):
        return getattr(self, key)
    def __getattr__(self, attr):
        return None
    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, sorted(self.__dict__.items()))

class Assert(YamlTag):
    def __init__(self, model, id=None, severity=logging.WARNING, string="NONAME", **kwargs):
        self.model = model
        self.id = id
        self.severity = severity
        self.string = string
        super(Assert, self).__init__(**kwargs)
    
class Record(YamlTag):
    def __init__(self, model, id, use='id', **kwargs):
        self.model = model
        self.id = id
        super(Record, self).__init__(**kwargs)
    def __str__(self):
        return '!record {model: %s, id: %s}:' % (str(self.model,), str(self.id,))
    
class Python(YamlTag):
    def __init__(self, model, severity=logging.ERROR, name="", **kwargs):
        self.model= model
        self.severity = severity
        self.name = name
        super(Python, self).__init__(**kwargs)
    def __str__(self):
        return '!python {model: %s}: |' % (str(self.model), )

class Menuitem(YamlTag):
    def __init__(self, id, name, **kwargs):
        self.id = id
        self.name = name
        super(Menuitem, self).__init__(**kwargs)

class Workflow(YamlTag):
    def __init__(self, model, action, ref=None, **kwargs):
        self.model = model
        self.action = action
        self.ref = ref
        super(Workflow, self).__init__(**kwargs)
    def __str__(self):
        return '!workflow {model: %s, action: %s, ref: %s}' % (str(self.model,), str(self.action,), str(self.ref,))

class ActWindow(YamlTag):
    def __init__(self, **kwargs):
        super(ActWindow, self).__init__(**kwargs)

class Function(YamlTag):
    def __init__(self, model, name, **kwargs):
        self.model = model
        self.name = name
        super(Function, self).__init__(**kwargs)

class Report(YamlTag):
    def __init__(self, model, name, string, **kwargs):
        self.model = model
        self.name = name
        self.string = string
        super(Report, self).__init__(**kwargs)

class Delete(YamlTag):
    def __init__(self, **kwargs):
        super(Delete, self).__init__(**kwargs)

class Context(YamlTag):
    def __init__(self, **kwargs):
        super(Context, self).__init__(**kwargs)

class Url(YamlTag):
    def __init__(self, **kwargs):
        super(Url, self).__init__(**kwargs)

class Eval(YamlTag):
    def __init__(self, expression):
        self.expression = expression
        super(Eval, self).__init__()
    def __str__(self):
        return '!eval %s' % str(self.expression)
    
class Ref(YamlTag):
    def __init__(self, expr="False", *args, **kwargs):
        self.expr = expr
        super(Ref, self).__init__(*args, **kwargs)
    def __str__(self):
        return 'ref(%s)' % repr(self.expr)
    
class IrSet(YamlTag):
    def __init__(self):
        super(IrSet, self).__init__()

def assert_constructor(loader, node):
    kwargs = loader.construct_mapping(node)
    return Assert(**kwargs)

def record_constructor(loader, node):
    kwargs = loader.construct_mapping(node)
    return Record(**kwargs)

def python_constructor(loader, node):
    kwargs = loader.construct_mapping(node)
    return Python(**kwargs)

def menuitem_constructor(loader, node):
    kwargs = loader.construct_mapping(node)
    return Menuitem(**kwargs)

def workflow_constructor(loader, node):
    kwargs = loader.construct_mapping(node)
    return Workflow(**kwargs)

def act_window_constructor(loader, node):
    kwargs = loader.construct_mapping(node)
    return ActWindow(**kwargs)

def function_constructor(loader, node):
    kwargs = loader.construct_mapping(node)
    return Function(**kwargs)

def report_constructor(loader, node):
    kwargs = loader.construct_mapping(node)
    return Report(**kwargs)

def delete_constructor(loader, node):
    kwargs = loader.construct_mapping(node)
    return Delete(**kwargs)

def context_constructor(loader, node):
    kwargs = loader.construct_mapping(node)
    return Context(**kwargs)

def url_constructor(loader, node):
    kwargs = loader.construct_mapping(node)
    return Url(**kwargs)

def eval_constructor(loader, node):
    expression = loader.construct_scalar(node)
    return Eval(expression)
    
def ref_constructor(loader, tag_suffix, node):
    if tag_suffix == "id":
        kwargs = {"id": loader.construct_scalar(node)}
    else:
        kwargs = loader.construct_mapping(node)
    return Ref(**kwargs)
    
def ir_set_constructor(loader, node):
    kwargs = loader.construct_mapping(node)
    return IrSet(**kwargs)
    
# Registers constructors for custom tags.
# Constructors are actually defined globally: do not redefined them in another
# class/file/package.  This means that module recorder need import this file.
def add_constructors():
    yaml.add_constructor(u"!assert", assert_constructor)
    yaml.add_constructor(u"!record", record_constructor)
    yaml.add_constructor(u"!python", python_constructor)
    yaml.add_constructor(u"!menuitem", menuitem_constructor)
    yaml.add_constructor(u"!workflow", workflow_constructor)
    yaml.add_constructor(u"!act_window", act_window_constructor)
    yaml.add_constructor(u"!function", function_constructor)
    yaml.add_constructor(u"!report", report_constructor)
    yaml.add_constructor(u"!context", context_constructor)
    yaml.add_constructor(u"!delete", delete_constructor)
    yaml.add_constructor(u"!url", url_constructor)
    yaml.add_constructor(u"!eval", eval_constructor)
    yaml.add_multi_constructor(u"!ref", ref_constructor)
    yaml.add_constructor(u"!ir_set", ir_set_constructor)
add_constructors()

