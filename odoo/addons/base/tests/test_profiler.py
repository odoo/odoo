from odoo.tests.common import BaseCase, TransactionCase
from odoo.tools.profiler import SpeedscopeResult, Profiler, TestProfiler


class TestRecorder(TransactionCase):

    def test_sync_recorder(self):
        def a():
            b()
            c()

        def b():
            pass

        def c():
            self.env.cr.execute('SELECT id FROM res_users LIMIT 1')

        with Profiler(description='test', sync=True, db=False) as res:
            a()
        #print(res)


#class TestSpeedscope(BaseCase):
#    def example_profile(self):
#        return {
#            'init_stack_trace_level': 0,
#            'init_stack_trace': [['/path/tp/file_1.py', 135, '__main__', 'main()'],], # not sure
#            'init_thread': 123456,
#            'result': [
#                {  # init frame
#                    'start': 2.0,
#                    'context': {},
#                    'stack': [
#                        ['/path/tp/file_1.py', 10, 'main', 'do_stuff1(test=do_tests)'],
#                        ['/path/to/file_1.py', 101, 'do_stuff1', 'cr.execute(query, params)'],
#                    ],
#                }, {
#                    'start': 3.0,
#                    'context': {},
#                    'stack': [
#                        ['/path/tp/file_1.py', 10, 'main', 'do_stuff1(test=do_tests)'],
#                        ['/path/to/file_1.py', 101, 'do_stuff1', 'cr.execute(query, params)'],
#                        ['/path/to/sql_db.py', 650, 'execute', 'res = self._obj.execute(query, params)'],
#                    ],
#                }, { # duplicate frame
#                    'start': 4.0,
#                    'context': {},
#                    'stack': [
#                        ['/path/tp/file_1.py', 10, 'main', 'do_stuff1(test=do_tests)'],
#                        ['/path/to/file_1.py', 101, 'do_stuff1', 'cr.execute(query, params)'],
#                        ['/path/to/sql_db.py', 650, 'execute', 'res = self._obj.execute(query, params)'],
#                    ],
#                }, { # other frame
#                    'start': 6.0,
#                    'context': {},
#                    'stack': [
#                        ['/path/tp/file_1.py', 10, 'main', 'do_stuff1(test=do_tests)'],
#                        ['/path/to/file_1.py', 101, 'do_stuff1', 'check'],
#                        ['/path/to/sql_db.py', 650, 'check', 'assert x = y'],
#                    ],
#                }, { # out of frame
#                    'start': 10.0,
#                    'context': {},
#                    'stack': [
#                        ['/path/tp/file_1.py', 10, 'main', 'do_stuff1(test=do_tests)'],
#                        ['/path/to/file_1.py', 101, 'do_stuff1', 'for i in range(10):'],
#                    ],
#                }, { # final frame
#                    'start': 10.35,
#                    'context': {},
#                    'stack': None,
#                },
#            ],
#        }
#
#    def test_convert_empty(self):
#        SpeedscopeResult().make()
#
#    def test_converts_profile_simple(self):
#        profile = self.example_profile()
#
#        res = SpeedscopeResult(profile=profile).make()
#        frames = res['shared']['frames']
#        self.assertEqual(len(frames), 4)
#
#        profile_combined = res['profiles'][0]
#        self.assertIn('all', profile_combined['name'])
#        events = [(e['type'], e['frame']) for e in profile_combined['events']]
#        self.assertEqual(
#            events,
#            [
#                ('O', 0),  # /main
#                ('O', 1),  # /main/do_stuff1
#                ('O', 2),  # /main/do_stuff1/execute
#                ('C', 2),  # /main/do_stuff1
#                ('O', 3),  # /main/do_stuff1/check
#                ('C', 3),  # /main/do_stuff1
#                ('C', 1),  # /main
#                ('C', 0),  # /
#            ]
#        )
#
#        self.assertEqual(profile_combined['events'][0]['at'], 0.0)
#        self.assertEqual(profile_combined['events'][-1]['at'], 8.35)
#
#
#    def test_converts_profile_no_end(self):
#        profile = self.example_profile()
#        profile['result'].pop()
#
#        res = SpeedscopeResult(profile=profile).make()
#        profile_combined = res['profiles'][0]
#        self.assertIn('all', profile_combined['name'])
#        events = [(e['type'], e['frame']) for e in profile_combined['events']]
#
#        self.assertEqual(
#            events,
#            [
#                ('O', 0),  # /main
#                ('O', 1),  # /main/do_stuff1
#                ('O', 2),  # /main/do_stuff1/execute
#                ('C', 2),  # /main/do_stuff1
#                ('O', 3),  # /main/do_stuff1/check
#                ('C', 3),  # /main/do_stuff1
#                ('C', 1),  # /main
#                ('C', 0),  # /
#            ])
#        self.assertEqual(profile_combined['events'][-1]['at'], 8)
#
#    def test_converts_init_stack_trace(self):
#        traces = self.example_profile()
#
#        res = SpeedscopeResult(traces=traces, complete=True)
#        res.add_profile(['traces'], complete=True)
#        res = res.make()
#
#        profile_combined = res['profiles'][0]
#        self.assertIn('all', profile_combined['name'])
#        events = [(e['type'], e['frame']) for e in profile_combined['events']]
#
#        self.assertEqual(
#            events,
#            [
#                ('O', 4), # /__main__/
#                ('O', 0), # /__main__/main
#                ('O', 1), # /__main__/main/do_stuff1
#                ('O', 2), # /__main__/main/do_stuff1/execute
#                ('C', 2), # /__main__/main/do_stuff1
#                ('O', 3), # /__main__/main/do_stuff1/check
#                ('C', 3), # /__main__/main/do_stuff1
#                ('C', 1), # /__main__/main
#                ('C', 0), # /__main__/
#                ('C', 4), # /
#            ])
#        self.assertEqual(profile_combined['events'][-1]['at'], 8.35)
#
#
#class TestRecorders(TransactionCase):
#    """ Tests on pdf. """
#
#    def test_profilers(self):
#        with Profiler(db=False) as p:
#            queries_start = self.env.cr.sql_log_count
#            for i in range(10):
#                self.env['res.partner'].create({'name': 'snail%s' % i})
#            self.env['res.partner'].flush()
#            total_queries = self.env.cr.sql_log_count - queries_start
#
#        rq = p.results['sql']
#        rt = p.results['traces']
#
#        self.assertEqual(rq['init_stack_trace'], rt['init_stack_trace'])
#        self.assertEqual(rq['init_thread'], rt['init_thread'])
#        self.assertEqual(rq['init_stack_trace'][-1][2], 'test_profilers')
#        self.assertEqual(rq['init_stack_trace'][-1][0].split('/')[-1], 'test_profiler.py')
#        self.assertEqual(rq['init_stack_trace_level'], rt['init_stack_trace_level'])
#        self.assertEqual(rq['init_stack_trace_level'], len(rq['init_stack_trace'])-1)
#
#        self.assertEqual(len(rq['result']), total_queries)
#        first_query = rq['result'][0]
#        self.assertEqual(first_query['stack'][0][2], 'test_profilers')
#        self.assertIn("self.env['res.partner'].create({", first_query['stack'][0][3])
#        self.assertEqual(first_query['stack'][0][0].split('/')[-1], 'test_profiler.py')
#
#        self.assertGreater(first_query['time'], 0)
#        #  the following assertion are odoo implementation dependant and may break easily but need to be considered.
#        self.assertEqual(first_query['stack'][-1][2], 'execute')
#        self.assertEqual(first_query['stack'][-1][0].split('/')[-1], 'sql_db.py')
#        self.assertEqual(first_query['query'][:18], 'SELECT "res_users"')
#        self.assertEqual(first_query['formated_query'][:18], 'SELECT "res_users"')
