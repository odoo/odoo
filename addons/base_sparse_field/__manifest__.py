# -*- coding: utf-8 -*-
{
    'name': "Sparse Fields",
    'summary': """Implementation of sparse fields.""",
    'description': """
        The purpose of this module is to implement "sparse" fields, i.e., fields
        that are mostly null. This implementation circumvents the PostgreSQL
        limitation on the number of columns in a table. The values of all sparse
        fields are stored in a "serialized" field in the form of a JSON mapping.
    """,
    'category': 'Hidden',
    'version': '1.0',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
}
