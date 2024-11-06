import re

from pypeg2 import List, contiguous, csl, name, optional, parse

from .exceptions import QueryFormatError


class IncludedField(List):
    grammar = name()


class ExcludedField(List):
    grammar = contiguous('-', name())


class AllFields(str):
    grammar = '*'


class BaseArgument(List):
    @property
    def value(self):
        return self[0]


class ArgumentWithoutQuotes(BaseArgument):
    grammar = name(), ':', re.compile(r'[^,:"\'\)]+')


class ArgumentWithSingleQuotes(BaseArgument):
    grammar = name(), ':', "'", re.compile(r'[^\']+'), "'"


class ArgumentWithDoubleQuotes(BaseArgument):
    grammar = name(), ':', '"', re.compile(r'[^"]+'), '"'


class Arguments(List):
    grammar = optional(csl(
        [
            ArgumentWithoutQuotes,
            ArgumentWithSingleQuotes,
            ArgumentWithDoubleQuotes
        ],
        separator=','
    ))


class ArgumentsBlock(List):
    grammar = optional('(', Arguments, ')')

    @property
    def arguments(self):
        if self[0] is None:
            return []  # No arguments
        return self[0]


class ParentField(List):
    """
    According to ParentField grammar:
    self[0]  returns IncludedField instance,
    self[1]  returns Block instance
    """
    @property
    def name(self):
        return self[0].name

    @property
    def block(self):
        return self[1]


class BlockBody(List):
    grammar = optional(csl(
        [ParentField, IncludedField, ExcludedField, AllFields],
        separator=','
    ))


class Block(List):
    grammar = ArgumentsBlock, '{', BlockBody, '}'

    @property
    def arguments(self):
        return self[0].arguments

    @property
    def body(self):
        return self[1]


# ParentField grammar,
# We don't include `ExcludedField` here because
# exclude operator(-) on a parent field should
# raise syntax error, e.g {name, -location{city}}
# `IncludedField` is a parent field and `Block`
# contains its sub fields
ParentField.grammar = IncludedField, Block


class Parser(object):
    def __init__(self, query):
        self._query = query

    def get_parsed(self):
        parse_tree = parse(self._query, Block)
        return self._transform_block(parse_tree)

    def _transform_block(self, block):
        fields = {
            "include": [],
            "exclude": [],
            "arguments": {}
        }

        for argument in block.arguments:
            argument = {str(argument.name): argument.value}
            fields['arguments'].update(argument)

        for field in block.body:
            # A field may be a parent or included field or excluded field
            field = self._transform_field(field)

            if isinstance(field, dict):
                # A field is a parent
                fields["include"].append(field)
            elif isinstance(field, IncludedField):
                fields["include"].append(str(field.name))
            elif isinstance(field, ExcludedField):
                fields["exclude"].append(str(field.name))
            elif isinstance(field, AllFields):
                # include all fields
                fields["include"].append("*")

        if fields["exclude"]:
            # fields['include'] should contain only nested fields

            # We should add `*` operator in fields['include']
            add_include_all_operator = True
            for field in fields["include"]:
                if field == "*":
                    # `*` operator is alredy in fields['include']
                    add_include_all_operator = False
                    continue

                if isinstance(field, str):
                    # Including and excluding fields on the same field level
                    msg = (
                        "Can not include and exclude fields on the same "
                        "field level"
                    )
                    raise QueryFormatError(msg)

            if add_include_all_operator:
                # Make sure we include * operator
                fields["include"].append("*")
        return fields

    def _transform_field(self, field):
        # A field may be a parent or included field or excluded field
        if isinstance(field, ParentField):
            return self._transform_parent_field(field)
        elif isinstance(field, (IncludedField, ExcludedField, AllFields)):
            return field

    def _transform_parent_field(self, parent_field):
        parent_field_name = str(parent_field.name)
        parent_field_value = self._transform_block(parent_field.block)
        return {parent_field_name: parent_field_value}
        