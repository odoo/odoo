# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

ALLOWED_ENCODING_FUNCTION = frozenset([
    'to_tsquery',
    'plainto_tsquery',
    'phraseto_tsquery',
    'websearch_to_tsquery',
])

class TSQueryOperator():
    def __init__(self, left, right):
        self.left = left
        self.right = right

class TSQueryOperatorAND(TSQueryOperator):
    def to_sql(self) -> str:
        (left_query, left_query_param) = self.left.to_sql()
        (right_query, right_query_param) = self.right.to_sql()
        return (f'''({left_query} && {right_query})''',
            left_query_param + right_query_param
        )

class TSQueryOperatorOR(TSQueryOperator):
    def to_sql(self) -> str:
        (left_query, left_query_param) = self.left.to_sql()
        (right_query, right_query_param) = self.right.to_sql()
        return (f'''({left_query} || {right_query})''',
            left_query_param + right_query_param
        )

class TSQuery:
    def __init__(self, regconfig, text, encoding_function='websearch_to_tsquery'):
        """
        :param str regconfig: language used to encode the query
        :param str text: text to encode
        """
        self.regconfig = regconfig
        self.text = text
        if encoding_function not in ALLOWED_ENCODING_FUNCTION:
            raise Exception('TSQuery: Unsupported encoding function')
        self.encoding_function = encoding_function

    # Operators:

    def __and__(self, other) -> TSQueryOperator:
        return TSQueryOperatorAND(self, other)

    def __or__(self, other) -> TSQueryOperator:
        return TSQueryOperatorOR(self, other)

    def to_sql(self) -> str:
        return (f'''{self.encoding_function}(%s::regconfig, %s)''', [
            self.regconfig,
            self.text
        ])
