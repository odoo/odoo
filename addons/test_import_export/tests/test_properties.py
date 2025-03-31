import json
from odoo.tests.common import RecordCapturer, HttpCase


class TestPropertiesExportImport(HttpCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.ModelDefinition = cls.env['import.properties.definition']
        cls.ModelProperty = cls.env['import.properties']
        cls.ModelPropertyInherits = cls.env['import.properties.inherits']
        cls.definition_records = cls.ModelDefinition.create(
            [
                {
                    'properties_definition': [
                        {'name': 'char_prop', 'type': 'char', 'string': 'TextType', 'default': 'Def'},
                        {'name': 'separator_prop', 'type': 'separator', 'string': 'Separator'},
                        {
                            'name': 'selection_prop',
                            'type': 'selection',
                            'string': 'One Selection',
                            'selection': [
                                ['selection_1', 'aaaaaaa'],
                                ['selection_2', 'bbbbbbb'],
                                ['selection_3', 'ccccccc'],
                            ],
                        },
                        {
                            'name': 'm2o_prop',
                            'type': 'many2one',
                            'string': 'many2one',
                            'comodel': 'res.partner',
                        },
                    ]
                },
                {
                    'properties_definition': [
                        {'name': 'bool_prop', 'type': 'boolean', 'string': 'CheckBox'},
                        {
                            'name': 'tags_prop',
                            'tags': [['aa', 'AA', 5], ['bb', 'BB', 6], ['cc', 'CC', 7]],
                            'type': 'tags',
                            'string': 'Tags',
                        },
                        {
                            'name': 'm2m_prop',
                            'type': 'many2many',
                            'string': 'M2M',
                            'comodel': 'res.partner',
                        },
                    ]
                },
            ]
        )
        cls.partners = cls.env['res.partner'].create(
            [
                {'name': 'Name Partner 1'},
                {'name': 'Name Partner 2'},
                {'name': 'Name Partner 3'},
            ]
        )

        cls.properties_records = cls.ModelProperty.create(
            [
                {
                    'record_definition_id': cls.definition_records[0].id,
                    'properties': {
                        'char_prop': 'Not the default',
                        'selection_prop': 'selection_2',
                    },
                },
                {
                    'record_definition_id': cls.definition_records[0].id,
                    'properties': {
                        'm2o_prop': cls.partners[0].id,
                    },
                },
                {
                    'record_definition_id': cls.definition_records[1].id,
                    'properties': {
                        'tags_prop': ['aa', 'bb'],
                        'bool_prop': True,
                    },
                },
                {
                    'record_definition_id': cls.definition_records[1].id,
                    'properties': {
                        'm2m_prop': cls.partners.ids,
                    },
                },
            ]
        )

    def test_export_get_fields(self):
        self.authenticate('admin', 'admin')

        res = self.url_open(
            "/web/export/get_fields",
            data=json.dumps({"params": {"model": 'import.properties',
                                        'import_compat': True,
                                        'domain': []}}),
            headers={"Content-Type": "application/json"}
        )
        dict_fields = json.loads(res.content)['result']
        self.assertEqual(
            [dict_field['id'] for dict_field in dict_fields], 
            [
                'properties.bool_prop',
                'id',
                'properties.m2m_prop',
                'properties.m2o_prop',
                'properties.selection_prop',
                'properties',
                'record_definition_id',
                'properties.tags_prop',
                'properties.char_prop',
            ]
        )

        res = self.url_open(
            "/web/export/get_fields",
            data=json.dumps({"params": {"model": 'import.properties',
                                        'import_compat': True,
                                        'domain': [('id', 'in', self.properties_records[0].ids)]}}),
            headers={"Content-Type": "application/json"}
        )
        dict_fields = json.loads(res.content)['result']
        self.assertEqual(
            [dict_field['id'] for dict_field in dict_fields],
            [
                'id',
                'properties.m2o_prop',
                'properties.selection_prop',
                'properties',
                'record_definition_id',
                'properties.char_prop',
            ]
        )
    
    def test_export_get_fields_inherits(self):
        self.authenticate('admin', 'admin')

        # FIXME: Put the creation of record here because there is a bug in create
        # for inherited properties that empties the properties source values
        inherits_records = self.ModelPropertyInherits.create([
            {'parent_id': record_parent.id}
            for record_parent in self.properties_records
        ])
        res = self.url_open(
            "/web/export/get_fields",
            data=json.dumps({"params": {"model": 'import.properties.inherits',
                                        'import_compat': True,
                                        'domain': []}}),
            headers={"Content-Type": "application/json"}
        )
        dict_fields = json.loads(res.content)['result']
        self.assertEqual(
            [dict_field['id'] for dict_field in dict_fields], 
            [
                'properties.bool_prop',
                'id',
                'properties.m2m_prop',
                'properties.m2o_prop',
                'properties.selection_prop',
                'parent_id',
                'properties',
                'record_definition_id',
                'properties.tags_prop',
                'properties.char_prop',
            ]
        )

        res = self.url_open(
            "/web/export/get_fields",
            data=json.dumps({"params": {"model": 'import.properties.inherits',
                                        'import_compat': True,
                                        'domain': [('id', 'in', inherits_records[0].ids)]}}),
            headers={"Content-Type": "application/json"}
        )
        dict_fields = json.loads(res.content)['result']
        self.assertEqual(
            [dict_field['id'] for dict_field in dict_fields],
            [
                'id',
                'properties.m2o_prop',
                'properties.selection_prop',
                'parent_id',
                'properties',
                'record_definition_id',
                'properties.char_prop',
            ]
        )

    def test_export_properties(self):
        all_properties = [
            [f"properties.{property_dict_type['name']}"]
            for property_dict_type in self.definition_records[0].properties_definition
            + self.definition_records[1].properties_definition
            if property_dict_type['type'] != 'separator'
        ]
        # Without import compatibility
        self.assertEqual(
            self.properties_records.with_context(import_compat=False)._export_rows(all_properties),
            [
                ['Not the default', 'bbbbbbb', '', '', '', ''],
                ['Def', '', 'Name Partner 1', '', '', ''],
                ['', '', '', True, 'AA,BB', ''],
                ['', '', '', '', '', 'Name Partner 1'],
                ['', '', '', '', '', 'Name Partner 2'],
                ['', '', '', '', '', 'Name Partner 3'],
            ],
        )
        # With import compatibility
        self.assertEqual(
            self.properties_records._export_rows(all_properties),
            [
                ['Not the default', 'bbbbbbb', '', '', '', ''],
                ['Def', '', 'Name Partner 1', '', '', ''],
                ['', '', '', True, 'AA,BB', ''],
                ['', '', '', '', '', 'Name Partner 1,Name Partner 2,Name Partner 3'],
            ],
        )

    def test_export_complex_path_properties(self):
        path_records = self.env['import.path.properties'].create([
            {
                'properties_id': self.properties_records[0].id,
                'another_properties_id': self.properties_records[1].id,  # Same definition
            },
            {
                'properties_id': self.properties_records[3].id,
                'another_properties_id': self.properties_records[2].id,
            }
        ])
        export_fields = [
            "properties_id/properties.m2m_prop/name",  # '' for [0], <All partner name> for [1]
            "another_properties_id/properties.m2o_prop/name",  # Partner Name 1 for [0], '' for [1]
            "another_properties_id/properties.bool_prop",  # '' for [0], True for [1]
            "all_properties_ids/properties.char_prop",  # 'Not the default'/'Def' for [0], '' for [1]
        ]

        self.assertEqual(
            path_records.with_context(import_compat=False).export_data(export_fields)['datas'],
            [
                ['', 'Name Partner 1', '', 'Not the default'],
                ['', '', '', 'Def'],
                ['Name Partner 1', '', True, ''],
                ['Name Partner 2', '', '', ''],
                ['Name Partner 3', '', '', ''],
                ['', '', '', ''],  # For the path_records[1] and all_properties_ids
            ]
        )

        export_fields = [
            "properties_id/properties.m2m_prop",  # '' for [0], <All partner name> for [1]
            "another_properties_id/properties.m2o_prop",  # Partner Name 1 for [0], '' for [1]
            "another_properties_id/properties.bool_prop",  # '' for [0], True for [1]
        ]
        self.assertEqual(
            path_records.export_data(export_fields)['datas'],
            [
                ['', 'Name Partner 1', ''],
                ['Name Partner 1,Name Partner 2,Name Partner 3', '', True],
            ]
        )

    def test_import_properties(self):
        def_record_1 = self.definition_records[0]
        def_record_2 = self.definition_records[1]
        values_list = [
            [
                "Record Definition Id",
                # Field of the first definition
                f"TextType ({def_record_1.display_name})", f"One Selection ({def_record_1.display_name})", f"many2one ({def_record_1.display_name})",
                # Field of the second definition
                f"CheckBox ({def_record_2.display_name})", "properties.tags_prop", f"M2M ({def_record_2.display_name})",
            ],
            # Record attached to the first definition record
            [
                str(def_record_1.id),
                'One Text', 'bbbbbbb', self.partners[0].display_name,
                '', '', '',
            ], [
                str(def_record_1.id),
                'One Text', 'selection_3', self.partners[1].display_name,
                '', '', '',
            ],

            # Record attached to the second definition record
            [
                str(def_record_2.id),
                '', '', '',
                'True', 'aa', ','.join(self.partners[:2].mapped('display_name')),
            ], [
                str(def_record_2.id),
                '', '', '',
                '0', 'BB', '',
            ],
        ]

        import_wizard = self.env['base_import.import'].create({
            'res_model': self.ModelProperty._name,
            'file': '\n'.join([';'.join(values) for values in values_list]),
            'file_type': 'text/csv',
        })
        opts = {'quoting': '"', 'separator': ';', 'has_headers': True}
        preview = import_wizard.parse_preview(opts)

        self.assertEqual(
            preview['matches'],
            {
                0: ['record_definition_id'],
                1: ['properties.char_prop'],
                2: ['properties.selection_prop'],
                3: ['properties.m2o_prop'],
                4: ['properties.bool_prop'],
                5: ['properties.tags_prop'],
                6: ['properties.m2m_prop'],
            },
        )

        with RecordCapturer(self.ModelProperty, []) as capture:
            results = import_wizard.execute_import(
                [fnames[0] for fnames in preview['matches'].values()],
                [],
                opts,
            )

        # if result is empty, no import error
        self.assertItemsEqual(results['messages'], [])

        records_created = capture.records
        self.assertEqual(records_created.record_definition_id, def_record_1 + def_record_2)

        self.assertEqual(records_created.mapped('properties'), [
            {'char_prop': 'One Text', 'selection_prop': 'selection_2', 'm2o_prop': self.partners[0].id},
            {'char_prop': 'One Text', 'selection_prop': 'selection_3', 'm2o_prop': self.partners[1].id},
            {'bool_prop': True, 'tags_prop': ['aa'], 'm2m_prop': self.partners[:2].ids},
            {'bool_prop': False, 'tags_prop': ['bb'], 'm2m_prop': False},
        ])

        records_created._BaseModel__ensure_xml_id()
        external_ids = [meta['xmlid'] for meta in records_created.get_metadata()]

        # Test the update flow
        values_list = [
            [
                "Id", "Record Definition Id",
                # Field of the first definition
                f"TextType ({def_record_1.display_name})", f"many2one ({def_record_1.display_name})",
                # Field of the second definition
                f"CheckBox ({def_record_2.display_name})", "properties.tags_prop", f"M2M ({def_record_2.display_name})",
            ],
            # Record attached to the first definition record
            [
                external_ids[0], str(def_record_1.id),
                'SSBIYXRlIHRoaXMgZmVhdHVyZQ==', str(self.partners[2].id),
                '', '', '',
            ],

            # Record attached to the second definition record
            [
                external_ids[1], str(def_record_2.id),  # record that changed its parent
                '', '',
                'FaLse', 'AA', f'{self.partners[1].id}',
            ],
            [
                external_ids[2], str(def_record_2.id),
                '', '',
                'false', 'bb,CC', '',
            ],
            [
                external_ids[3], str(def_record_2.id),
                '', '',
                '1', 'BB', f'{self.partners[1].id},{self.partners[2].id}',
            ],
        ]

        import_wizard = self.env['base_import.import'].create({
            'res_model': self.ModelProperty._name,
            'file': '\n'.join([';'.join(values) for values in values_list]),
            'file_type': 'text/csv',
        })
        opts = {'quoting': '"', 'separator': ';', 'has_headers': True}
        preview = import_wizard.parse_preview(opts)

        self.assertEqual(
            preview['matches'],
            {
                0: ['id'],
                1: ['record_definition_id'],
                2: ['properties.char_prop'],
                3: ['properties.m2o_prop'],
                4: ['properties.bool_prop'],
                5: ['properties.tags_prop'],
                6: ['properties.m2m_prop'],
            },
        )

        results = import_wizard.execute_import(
            [
                'id',
                'record_definition_id',
                'properties.char_prop',
                'properties.m2o_prop/.id',
                'properties.bool_prop',
                'properties.tags_prop',
                'properties.m2m_prop/.id',
            ],
            [],
            opts,
        )
        self.assertItemsEqual(results['messages'], [])

        self.assertEqual(records_created.mapped('properties'), [
            {'char_prop': 'SSBIYXRlIHRoaXMgZmVhdHVyZQ==', 'selection_prop': 'selection_2', 'm2o_prop': self.partners[2].id},
            {'bool_prop': False, 'tags_prop': ['aa'], 'm2m_prop': self.partners[1].ids},
            {'bool_prop': False, 'tags_prop': ['bb', 'cc'], 'm2m_prop': False},
            {'bool_prop': True, 'tags_prop': ['bb'], 'm2m_prop': self.partners[1:].ids},
        ])
