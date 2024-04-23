# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from odoo.exceptions import AccessError
from odoo.tests.common import BaseCase, TransactionCase, tagged, new_test_user
from odoo.tools import profiler
from odoo.tools.profiler import Profiler, ExecutionContext
from odoo.tools.speedscope import Speedscope


@tagged('post_install', '-at_install', 'profiling')
# post_install to ensure mail is already loaded if installed (new_test_user would fail otherwise because of notification_type)
class TestProfileAccess(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_profile = cls.env['ir.profile'].create({})

    def test_admin_has_access(self):
        self.assertEqual(self.env['ir.profile'].search([('id', '=', self.test_profile.id)]), self.test_profile)
        self.test_profile.read(['name'])

    def test_user_no_access(self):
        user = new_test_user(self.env, login='noProfile', groups='base.group_user')
        with self.with_user('noProfile'), self.assertRaises(AccessError):
            self.env['ir.profile'].search([])
        with self.assertRaises(AccessError):
            self.test_profile.with_user(user).read(['name'])


@tagged('post_install', '-at_install', 'profiling')
class TestSpeedscope(BaseCase):
    def example_profile(self):
        return {
            'init_stack_trace': [['/path/to/file_1.py', 135, '__main__', 'main()']],
            'result': [{  # init frame
                'start': 2.0,
                'exec_context': (),
                'stack': [
                    ['/path/to/file_1.py', 10, 'main', 'do_stuff1(test=do_tests)'],
                    ['/path/to/file_1.py', 101, 'do_stuff1', 'cr.execute(query, params)'],
                ],
            }, {
                'start': 3.0,
                'exec_context': (),
                'stack': [
                    ['/path/to/file_1.py', 10, 'main', 'do_stuff1(test=do_tests)'],
                    ['/path/to/file_1.py', 101, 'do_stuff1', 'cr.execute(query, params)'],
                    ['/path/to/sql_db.py', 650, 'execute', 'res = self._obj.execute(query, params)'],
                ],
            }, {  # duplicate frame
                'start': 4.0,
                'exec_context': (),
                'stack': [
                    ['/path/to/file_1.py', 10, 'main', 'do_stuff1(test=do_tests)'],
                    ['/path/to/file_1.py', 101, 'do_stuff1', 'cr.execute(query, params)'],
                    ['/path/to/sql_db.py', 650, 'execute', 'res = self._obj.execute(query, params)'],
                ],
            }, {  # other frame
                'start': 6.0,
                'exec_context': (),
                'stack': [
                    ['/path/to/file_1.py', 10, 'main', 'do_stuff1(test=do_tests)'],
                    ['/path/to/file_1.py', 101, 'do_stuff1', 'check'],
                    ['/path/to/sql_db.py', 650, 'check', 'assert x = y'],
                ],
            }, {  # out of frame
                'start': 10.0,
                'exec_context': (),
                'stack': [
                    ['/path/to/file_1.py', 10, 'main', 'do_stuff1(test=do_tests)'],
                    ['/path/to/file_1.py', 101, 'do_stuff1', 'for i in range(10):'],
                ],
            }, {  # final frame
                'start': 10.35,
                'exec_context': (),
                'stack': None,
            }],
        }

    def test_convert_empty(self):
        Speedscope().make()

    def test_converts_profile_simple(self):
        profile = self.example_profile()

        sp = Speedscope(init_stack_trace=profile['init_stack_trace'])
        sp.add('profile', profile['result'])
        sp.add_output(['profile'], complete=False)
        res = sp.make()

        frames = res['shared']['frames']
        self.assertEqual(len(frames), 4)

        profile_combined = res['profiles'][0]
        events = [(e['type'], e['frame']) for e in profile_combined['events']]
        self.assertEqual(events, [
            ('O', 0),  # /main
            ('O', 1),  # /main/do_stuff1
            ('O', 2),  # /main/do_stuff1/execute
            ('C', 2),  # /main/do_stuff1
            ('O', 3),  # /main/do_stuff1/check
            ('C', 3),  # /main/do_stuff1
            ('C', 1),  # /main
            ('C', 0),  # /
        ])
        self.assertEqual(profile_combined['events'][0]['at'], 0.0)
        self.assertEqual(profile_combined['events'][-1]['at'], 8.35)

    def test_converts_profile_no_end(self):
        profile = self.example_profile()
        profile['result'].pop()

        sp = Speedscope(init_stack_trace=profile['init_stack_trace'])
        sp.add('profile', profile['result'])
        sp.add_output(['profile'], complete=False)
        res = sp.make()
        profile_combined = res['profiles'][0]
        events = [(e['type'], e['frame']) for e in profile_combined['events']]

        self.assertEqual(events, [
            ('O', 0),  # /main
            ('O', 1),  # /main/do_stuff1
            ('O', 2),  # /main/do_stuff1/execute
            ('C', 2),  # /main/do_stuff1
            ('O', 3),  # /main/do_stuff1/check
            ('C', 3),  # /main/do_stuff1
            ('C', 1),  # /main
            ('C', 0),  # /
        ])
        self.assertEqual(profile_combined['events'][-1]['at'], 8)

    def test_converts_init_stack_trace(self):
        profile = self.example_profile()

        sp = Speedscope(init_stack_trace=profile['init_stack_trace'])
        sp.add('profile', profile['result'])
        sp.add_output(['profile'], complete=True)
        res = sp.make()

        profile_combined = res['profiles'][0]
        events = [(e['type'], e['frame']) for e in profile_combined['events']]

        self.assertEqual(events, [
            ('O', 4),  # /__main__/
            ('O', 0),  # /__main__/main
            ('O', 1),  # /__main__/main/do_stuff1
            ('O', 2),  # /__main__/main/do_stuff1/execute
            ('C', 2),  # /__main__/main/do_stuff1
            ('O', 3),  # /__main__/main/do_stuff1/check
            ('C', 3),  # /__main__/main/do_stuff1
            ('C', 1),  # /__main__/main
            ('C', 0),  # /__main__/
            ('C', 4),  # /
        ])
        self.assertEqual(profile_combined['events'][-1]['at'], 8.35)

    def test_end_priority(self):
        """
        If a sample as a time (usually a query) we expect to keep the complete frame
        even if another concurent frame tics before the end of the current one:
        frame duration should always be more reliable.
        """

        async_profile = self.example_profile()['result']
        sql_profile = self.example_profile()['result']
        # make sql_profile a single frame from 2.5 to 5.5
        sql_profile = [sql_profile[1]]
        sql_profile[0]['start'] = 2.5
        sql_profile[0]['time'] = 3
        sql_profile[0]['query'] = 'SELECT 1'
        sql_profile[0]['full_query'] = 'SELECT 1'
        # some check to ensure the take makes sence
        self.assertEqual(async_profile[1]['start'], 3)
        self.assertEqual(async_profile[2]['start'], 4)

        self.assertNotIn('query', async_profile[1]['stack'])
        self.assertNotIn('time', async_profile[1]['stack'])
        self.assertEqual(async_profile[1]['stack'], async_profile[2]['stack'])
        # this last assertion is not really useful but ensures that the samples
        # are consistent with the sql one, just missing tue query

        sp = Speedscope(init_stack_trace=[])
        sp.add('sql', async_profile)
        sp.add('traces', sql_profile)
        sp.add_output(['sql', 'traces'], complete=False)
        res = sp.make()
        profile_combined = res['profiles'][0]
        events = [
            (e['at']+2, e['type'], res['shared']['frames'][e['frame']]['name'])
            for e in profile_combined['events']
        ]
        self.assertEqual(events, [
            # pylint: disable=bad-continuation
            (2.0, 'O', 'main'),
                (2.0, 'O', 'do_stuff1'),
                    (2.5, 'O', 'execute'),
                        (2.5, 'O', "sql('SELECT 1')"),
                        (5.5, 'C', "sql('SELECT 1')"),  # select ends at 5.5 as expected despite another concurent frame at 3 and 4
                    (5.5, 'C', 'execute'),
                    (6.0, 'O', 'check'),
                    (10.0, 'C', 'check'),
                (10.35, 'C', 'do_stuff1'),
            (10.35, 'C', 'main'),
        ])

    def test_converts_context(self):
        stack = [
            ['file.py', 10, 'level1', 'level1'],
            ['file.py', 11, 'level2', 'level2'],
        ]
        profile = {
            'init_stack_trace': [['file.py', 1, 'level0', 'level0)']],
            'result': [{  # init frame
                'start': 2.0,
                'exec_context': ((2, {'a': '1'}), (3, {'b': '1'})),
                'stack': list(stack),
            }, {
                'start': 3.0,
                'exec_context': ((2, {'a': '1'}), (3, {'b': '2'})),
                'stack': list(stack),
            }, {  # final frame
                'start': 10.35,
                'exec_context': (),
                'stack': None,
            }],
        }
        sp = Speedscope(init_stack_trace=profile['init_stack_trace'])
        sp.add('profile', profile['result'])
        sp.add_output(['profile'], complete=True)
        res = sp.make()
        events = [
            (e['type'], res['shared']['frames'][e['frame']]['name'])
            for e in res['profiles'][0]['events']
        ]
        self.assertEqual(events, [
            # pylint: disable=bad-continuation
            ('O', 'level0'),
                ('O', 'a=1'),
                    ('O', 'level1'),
                        ('O', 'b=1'),
                            ('O', 'level2'),
                            ('C', 'level2'),
                        ('C', 'b=1'),
                        ('O', 'b=2'),
                            ('O', 'level2'),
                            ('C', 'level2'),
                        ('C', 'b=2'),
                    ('C', 'level1'),
                ('C', 'a=1'),
            ('C', 'level0'),
        ])

    def test_converts_context_nested(self):
        stack = [
            ['file.py', 10, 'level1', 'level1'],
            ['file.py', 11, 'level2', 'level2'],
        ]
        profile = {
            'init_stack_trace': [['file.py', 1, 'level0', 'level0)']],
            'result': [{  # init frame
                'start': 2.0,
                'exec_context': ((3, {'a': '1'}), (3, {'b': '1'})),  # two contexts at the same level
                'stack': list(stack),
            }, {  # final frame
                'start': 10.35,
                'exec_context': (),
                'stack': None,
            }],
        }
        sp = Speedscope(init_stack_trace=profile['init_stack_trace'])
        sp.add('profile', profile['result'])
        sp.add_output(['profile'], complete=True)
        res = sp.make()
        events = [
            (e['type'], res['shared']['frames'][e['frame']]['name'])
            for e in res['profiles'][0]['events']
        ]
        self.assertEqual(events, [
            # pylint: disable=bad-continuation
            ('O', 'level0'),
                ('O', 'level1'),
                    ('O', 'a=1'),
                        ('O', 'b=1'),
                            ('O', 'level2'),
                            ('C', 'level2'),
                        ('C', 'b=1'),
                    ('C', 'a=1'),
                ('C', 'level1'),
            ('C', 'level0'),
        ])

    def test_converts_context_lower(self):
        stack = [
            ['file.py', 10, 'level4', 'level4'],
            ['file.py', 11, 'level5', 'level5'],
        ]
        profile = {
            'init_stack_trace': [
                ['file.py', 1, 'level0', 'level0'],
                ['file.py', 1, 'level1', 'level1'],
                ['file.py', 1, 'level2', 'level2'],
                ['file.py', 1, 'level3', 'level3'],
            ],
            'result': [{  # init frame
                'start': 2.0,
                'exec_context': ((2, {'a': '1'}), (6, {'b': '1'})),
                'stack': list(stack),
            }, {  # final frame
                'start': 10.35,
                'exec_context': (),
                'stack': None,
            }],
        }
        sp = Speedscope(init_stack_trace=profile['init_stack_trace'])
        sp.add('profile', profile['result'])
        sp.add_output(['profile'], complete=False)
        res = sp.make()
        events = [
            (e['type'], res['shared']['frames'][e['frame']]['name'])
            for e in res['profiles'][0]['events']
        ]
        self.assertEqual(events, [
            # pylint: disable=bad-continuation
            ('O', 'level4'),
                ('O', 'b=1'),
                    ('O', 'level5'),
                    ('C', 'level5'),
                ('C', 'b=1'),
            ('C', 'level4'),
        ])

    def test_converts_no_context(self):
        stack = [
            ['file.py', 10, 'level4', 'level4'],
            ['file.py', 11, 'level5', 'level5'],
        ]
        profile = {
            'init_stack_trace': [
                ['file.py', 1, 'level0', 'level0'],
                ['file.py', 1, 'level1', 'level1'],
                ['file.py', 1, 'level2', 'level2'],
                ['file.py', 1, 'level3', 'level3'],
            ],
            'result': [{  # init frame
                'start': 2.0,
                'exec_context': ((2, {'a': '1'}), (6, {'b': '1'})),
                'stack': list(stack),
            }, {  # final frame
                'start': 10.35,
                'exec_context': (),
                'stack': None,
            }],
        }
        sp = Speedscope(init_stack_trace=profile['init_stack_trace'])
        sp.add('profile', profile['result'])
        sp.add_output(['profile'], complete=False, use_context=False)
        res = sp.make()
        events = [
            (e['type'], res['shared']['frames'][e['frame']]['name'])
            for e in res['profiles'][0]['events']
        ]
        self.assertEqual(events, [
            # pylint: disable=bad-continuation
            ('O', 'level4'),
                ('O', 'level5'),
                ('C', 'level5'),
            ('C', 'level4'),
        ])


@tagged('post_install', '-at_install', 'profiling')
class TestProfiling(TransactionCase):

    def test_default_values(self):
        p = Profiler()
        self.assertEqual(p.db, self.env.cr.dbname)

    def test_env_profiler_database(self):
        p = Profiler(collectors=[])
        self.assertEqual(p.db, self.env.cr.dbname)

    def test_env_profiler_description(self):
        with Profiler(collectors=[], db=None) as p:
            self.assertIn('test_env_profiler_description', p.description)

    def test_execution_context_save(self):
        with Profiler(db=None, collectors=['sql']) as p:
            for letter in ('a', 'b'):
                stack_level = profiler.stack_size()
                with ExecutionContext(letter=letter):
                    self.env.cr.execute('SELECT 1')
        entries = p.collectors[0].entries
        self.assertEqual(entries.pop(0)['exec_context'], ((stack_level, {'letter': 'a'}),))
        self.assertEqual(entries.pop(0)['exec_context'], ((stack_level, {'letter': 'b'}),))

    def test_execution_context_nested(self):
        """
        This test checks that an execution can be nested at the same level of the stack.
        """
        with Profiler(db=None, collectors=['sql']) as p:
            stack_level = profiler.stack_size()
            with ExecutionContext(letter='a'):
                self.env.cr.execute('SELECT 1')
                with ExecutionContext(letter='b'):
                    self.env.cr.execute('SELECT 1')
                with ExecutionContext(letter='c'):
                    self.env.cr.execute('SELECT 1')
                self.env.cr.execute('SELECT 1')
        entries = p.collectors[0].entries
        self.assertEqual(entries.pop(0)['exec_context'], ((stack_level, {'letter': 'a'}),))
        self.assertEqual(entries.pop(0)['exec_context'], ((stack_level, {'letter': 'a'}), (stack_level, {'letter': 'b'})))
        self.assertEqual(entries.pop(0)['exec_context'], ((stack_level, {'letter': 'a'}), (stack_level, {'letter': 'c'})))
        self.assertEqual(entries.pop(0)['exec_context'], ((stack_level, {'letter': 'a'}),))

    def test_sync_recorder(self):
        def a():
            b()
            c()

        def b():
            pass

        def c():
            d()
            d()

        def d():
            pass

        with Profiler(description='test', collectors=['traces_sync'], db=None) as p:
            a()

        stacks = [r['stack'] for r in p.collectors[0].entries]

        # map stack frames to their function name, and check
        stacks_methods = [[frame[2] for frame in stack] for stack in stacks]
        self.assertEqual(stacks_methods[:-2], [
            ['a'],
            ['a', 'b'],
            ['a'],
            ['a', 'c'],
            ['a', 'c', 'd'],
            ['a', 'c'],
            ['a', 'c', 'd'],
            ['a', 'c'],
            ['a'],
            [],
        ])

        # map stack frames to their line number, and check
        stacks_lines = [[frame[1] for frame in stack] for stack in stacks]
        self.assertEqual(stacks_lines[1][0] + 1, stacks_lines[3][0],
                         "Call of b() in a() should be one line before call of c()")

    def test_qweb_recorder(self):
        template = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'key': 'root',
            'arch_db': '''<t t-name="root">
                <t t-foreach="{'a': 3, 'b': 2, 'c': 1}" t-as="item">
                    [<t t-out="item_index"/>: <t t-set="record" t-value="item"/><t t-call="base.dummy"/> <t t-out="item_value"/>]
                    <b t-out="add_one_query()"/></t>
            </t>'''
        })
        child_template = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'key': 'dummy',
            'arch_db': '<t t-name="dummy"><span t-attf-class="myclass"><t t-out="record"/> <t t-out="add_one_query()"/></span></t>'
        })
        self.env.cr.execute("INSERT INTO ir_model_data(name, model, res_id, module)"
                            "VALUES ('dummy', 'ir.ui.view', %s, 'base')", [child_template.id])

        values = {'add_one_query': lambda: self.env.cr.execute('SELECT id FROM ir_ui_view LIMIT 1') or 'query'}
        result = u"""
                    [0: <span class="myclass">a query</span> 3]
                    <b>query</b>
                    [1: <span class="myclass">b query</span> 2]
                    <b>query</b>
                    [2: <span class="myclass">c query</span> 1]
                    <b>query</b>
        """

        # test rendering without profiling
        rendered = self.env['ir.qweb']._render(template.id, values)
        self.assertEqual(rendered.strip(), result.strip(), 'Without profiling')

        # This rendering is used to cache the compiled template method so as
        # not to have a number of requests that vary according to the modules
        # installed.
        with Profiler(description='test', collectors=['qweb'], db=None):
            self.env['ir.qweb']._render(template.id, values)

        with Profiler(description='test', collectors=['qweb'], db=None) as p:
            rendered = self.env['ir.qweb']._render(template.id, values)
            # check if qweb is ok
            self.assertEqual(rendered.strip(), result.strip())

        # check if the arch of all used templates is includes in the result
        self.assertEqual(p.collectors[0].entries[0]['results']['archs'], {
            template.id: template.arch_db,
            child_template.id: child_template.arch_db,
        })

        # check all directives without duration information
        for data in p.collectors[0].entries[0]['results']['data']:
            data.pop('delay')

        data = p.collectors[0].entries[0]['results']['data']
        expected = [
            # pylint: disable=bad-whitespace
            # first template and first directive
            {'view_id': template.id,       'xpath': '/t/t',         'directive': """t-foreach="{'a': 3, 'b': 2, 'c': 1}" t-as='item'""", 'query': 0},
            # first pass in the loop
            {'view_id': template.id,       'xpath': '/t/t/t[1]',    'directive': "t-out='item_index'", 'query': 0},
            {'view_id': template.id,       'xpath': '/t/t/t[2]',    'directive': "t-set='record' t-value='item'", 'query': 0},
            {'view_id': template.id,       'xpath': '/t/t/t[3]',    'directive': "t-call='base.dummy'", 'query': 0}, # 0 because the template is in ir.ui.view cache
            # first pass in the loop: content of the child template
            {'view_id': child_template.id, 'xpath': '/t/span',      'directive': "t-attf-class='myclass'", 'query': 0},
            {'view_id': child_template.id, 'xpath': '/t/span/t[1]', 'directive': "t-out='record'", 'query': 0},
            {'view_id': child_template.id, 'xpath': '/t/span/t[2]', 'directive': "t-out='add_one_query()'", 'query': 1},
            {'view_id': template.id,       'xpath': '/t/t/t[4]',    'directive': "t-out='item_value'", 'query': 0},
            {'view_id': template.id,       'xpath': '/t/t/b',       'directive': "t-out='add_one_query()'", 'query':1},
            # second pass in the loop
            {'view_id': template.id,       'xpath': '/t/t/t[1]',    'directive': "t-out='item_index'", 'query': 0},
            {'view_id': template.id,       'xpath': '/t/t/t[2]',    'directive': "t-set='record' t-value='item'", 'query': 0},
            {'view_id': template.id,       'xpath': '/t/t/t[3]',    'directive': "t-call='base.dummy'", 'query': 0},
            {'view_id': child_template.id, 'xpath': '/t/span',      'directive': "t-attf-class='myclass'", 'query': 0},
            {'view_id': child_template.id, 'xpath': '/t/span/t[1]', 'directive': "t-out='record'", 'query': 0},
            {'view_id': child_template.id, 'xpath': '/t/span/t[2]', 'directive': "t-out='add_one_query()'", 'query': 1},
            {'view_id': template.id,       'xpath': '/t/t/t[4]',    'directive': "t-out='item_value'", 'query': 0},
            {'view_id': template.id,       'xpath': '/t/t/b',       'directive': "t-out='add_one_query()'", 'query':1},
            # third pass in the loop
            {'view_id': template.id,       'xpath': '/t/t/t[1]',    'directive': "t-out='item_index'", 'query': 0},
            {'view_id': template.id,       'xpath': '/t/t/t[2]',    'directive': "t-set='record' t-value='item'", 'query': 0},
            {'view_id': template.id,       'xpath': '/t/t/t[3]',    'directive': "t-call='base.dummy'", 'query': 0},
            {'view_id': child_template.id, 'xpath': '/t/span',      'directive': "t-attf-class='myclass'", 'query': 0},
            {'view_id': child_template.id, 'xpath': '/t/span/t[1]', 'directive': "t-out='record'", 'query': 0},
            {'view_id': child_template.id, 'xpath': '/t/span/t[2]', 'directive': "t-out='add_one_query()'", 'query': 1},
            {'view_id': template.id,       'xpath': '/t/t/t[4]',    'directive': "t-out='item_value'", 'query': 0},
            {'view_id': template.id,       'xpath': '/t/t/b',       'directive': "t-out='add_one_query()'", 'query':1},
        ]
        self.assertEqual(data, expected)

    def test_default_recorders(self):
        with Profiler(db=None) as p:
            queries_start = self.env.cr.sql_log_count
            for i in range(10):
                self.env['res.partner'].create({'name': 'snail%s' % i})
            self.env.flush_all()
            total_queries = self.env.cr.sql_log_count - queries_start

        rq = next(r for r in p.collectors if r.name == "sql").entries
        self.assertEqual(p.init_stack_trace[-1][2], 'test_default_recorders')
        self.assertEqual(p.init_stack_trace[-1][0].split('/')[-1], 'test_profiler.py')

        self.assertEqual(len(rq), total_queries)
        first_query = rq[0]
        self.assertEqual(first_query['stack'][0][2], 'create')
        #self.assertIn("self.env['res.partner'].create({", first_query['stack'][0][3])

        self.assertGreater(first_query['time'], 0)
        self.assertEqual(first_query['stack'][-1][2], 'execute')
        self.assertEqual(first_query['stack'][-1][0].split('/')[-1], 'sql_db.py')


def deep_call(func, depth):
    """ Call the given function at the given call depth. """
    if depth > 0:
        deep_call(func, depth - 1)
    else:
        func()


@tagged('-standard', 'profiling_performance')
class TestPerformance(BaseCase):

    def test_collector_max_frequency(self):
        """
        Check the creation time of an entry
        """
        collector = profiler.Collector()
        p = Profiler(collectors=[collector], db=None)

        def collect():
            collector.add()

        # collect on changing stack
        with p:
            start = time.time()
            while start + 1 > time.time():
                deep_call(collect, 20)

        self.assertGreater(len(collector.entries), 20000)  # ~40000

        # collect on identical stack
        collector = profiler.Collector()
        p = Profiler(collectors=[collector], db=None)

        def collect_1_s():
            start = time.time()
            while start + 1 > time.time():
                collector.add()

        with p:
            deep_call(collect_1_s, 20)

        self.assertGreater(len(collector.entries), 50000)  # ~70000

    def test_frequencies_1ms_sleep(self):
        """
        Check the number of entries generated in 1s at 1kHz
        we need to artificially change the frame as often as possible to avoid
        triggering the memory optimisation skipping identical frames
        """
        def sleep_1():
            time.sleep(0.0001)

        def sleep_2():
            time.sleep(0.0001)

        with Profiler(collectors=['traces_async'], db=None) as res:
            start = time.time()
            while start + 1 > time.time():
                sleep_1()
                sleep_2()

        entry_count = len(res.collectors[0].entries)
        self.assertGreater(entry_count, 700)  # ~920

    def test_traces_async_memory_optimisation(self):
        """
        Identical frames should be saved only once.
        We should only have a few entries on a 1 second sleep.
        """
        with Profiler(collectors=['traces_async'], db=None) as res:
            time.sleep(1)
        entry_count = len(res.collectors[0].entries)
        self.assertLess(entry_count, 5)  # ~3
