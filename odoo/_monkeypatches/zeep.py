from zeep.xsd import visitor
from zeep.xsd.const import xsd_ns


def patch_module():
    # see https://github.com/mvantellingen/python-zeep/issues/1185
    if visitor.tags.notation.localname != 'notation':
        visitor.tags.notation = xsd_ns('notation')
        visitor.SchemaVisitor.visitors[visitor.tags.notation] = visitor.SchemaVisitor.visit_notation
