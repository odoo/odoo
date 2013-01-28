"""
Define a base class for client-side benchmarking.
"""
import hashlib
import multiprocessing
import sys
import time

from .client import Client

class Bench(Client):
    """
    Base class for concurrent benchmarks. The measure_once() method must be
    overriden.

    Each sub-benchmark will be run in its own process then a report is done
    with all the results (shared with the main process using a
    `multiprocessing.Array`).
    """

    def __init__(self, subparsers=None):
        super(Bench, self).__init__(subparsers)
        self.parser.add_argument('-n', '--samples', metavar='INT',
            default=100, help='number of measurements to take')
            # TODO if -n <int>s is given (instead of -n <int>), run the
            # benchmark for <int> seconds and return the number of iterations.
        self.parser.add_argument('-o', '--output', metavar='PATH',
            required=True, help='path to save the generated report')
        self.parser.add_argument('--append', action='store_true',
            default=False, help='append the report to an existing file')
        self.parser.add_argument('-j', '--jobs', metavar='JOBS',
            default=1, help='number of concurrent workers')
        self.parser.add_argument('--seed', metavar='SEED',
            default=0, help='a value to ensure different runs can create unique data')
        self.worker = -1

    def work(self, iarr=None):
        if iarr:
            # If an array is given, it means we are a worker process...
            self.work_slave(iarr)
        else:
            # ... else we are the main process and we will spawn workers,
            # passing them an array.
            self.work_master()

    def work_master(self):
        N = int(self.args.samples)
        self.arrs = [(i, multiprocessing.Array('f', range(N)))
            for i in xrange(int(self.args.jobs))]
        ps = [multiprocessing.Process(target=self.run, args=(arr,))
            for arr in self.arrs]
        [p.start() for p in ps]
        [p.join() for p in ps]

        self.report_html()

    def work_slave(self, iarr):
        j, arr = iarr
        self.worker = j
        N = int(self.args.samples)
        total_t0 = time.time()
        for i in xrange(N):
            t0 = time.time()
            self.measure_once(i)
            t1 = time.time()
            arr[i] = t1 - t0
            print >> sys.stdout, '\r%s' % ('|' * (i * 60 / N)),
            print >> sys.stdout, '%s %s%%' % \
                (' ' * (60 - (i * 60 / N)), int(float(i+1)/N*100)),
            sys.stdout.flush()
        total_t1 = time.time()
        print '\nDone in %ss.' % (total_t1 - total_t0)

    def report_html(self):
        series = []
        for arr in self.arrs:
            serie = """{
                data: %s,
                points: { show: true }
            }""" % ([[x, i] for i, x in enumerate(arr)],)
            series.append(serie)
        chart_id = hashlib.md5(" ".join(sys.argv)).hexdigest()
        HEADER = """<!doctype html>
<title>Benchmarks</title>
<meta charset=utf-8>
<script type="text/javascript" src="js/jquery.min.js"></script>
<script type="text/javascript" src="js/jquery.flot.js"></script>
"""

        CONTENT = """<h1>%s</h1>
%s
<div id='chart_%s' style='width:400px;height:300px;'>...</div>
<script type="text/javascript">
$.plot($("#chart_%s"), [%s],
  {yaxis: { ticks: false }});
</script>""" % (self.bench_name, ' '.join(sys.argv), chart_id, chart_id,
        ','.join(series))
        if self.args.append:
            with open(self.args.output, 'a') as f:
                f.write(CONTENT,)
        else:
            with open(self.args.output, 'w') as f:
                f.write(HEADER + CONTENT,)

    def measure_once(self, i):
        """
        The `measure_once` method is called --jobs times. A `i` argument is
        supplied to allow to create unique values for each execution (e.g. to
        supply fresh identifiers to a `create` method.
        """
        pass

class BenchRead(Bench):
    """Read a record repeatedly."""

    command_name = 'bench-read'
    bench_name = 'res.users.read(1)'

    def __init__(self, subparsers=None):
        super(BenchRead, self).__init__(subparsers)
        self.parser.add_argument('-m', '--model', metavar='MODEL',
            required=True, help='the model')
        self.parser.add_argument('-i', '--id', metavar='RECORDID',
            required=True, help='the record id')

    def measure_once(self, i):
        self.execute(self.args.model, 'read', [self.args.id], [])

class BenchFieldsViewGet(Bench):
    """Read a record's fields and view architecture repeatedly."""

    command_name = 'bench-view'
    bench_name = 'res.users.fields_view_get(1)'

    def __init__(self, subparsers=None):
        super(BenchFieldsViewGet, self).__init__(subparsers)
        self.parser.add_argument('-m', '--model', metavar='MODEL',
            required=True, help='the model')
        self.parser.add_argument('-i', '--id', metavar='RECORDID',
            required=True, help='the record id')

    def measure_once(self, i):
        self.execute(self.args.model, 'fields_view_get', self.args.id)

class BenchDummy(Bench):
    """Dummy (call test.limits.model.consume_nothing())."""

    command_name = 'bench-dummy'
    bench_name = 'test.limits.model.consume_nothing()'

    def __init__(self, subparsers=None):
        super(BenchDummy, self).__init__(subparsers)
        self.parser.add_argument('-a', '--args', metavar='ARGS',
            default='', help='some arguments to serialize')

    def measure_once(self, i):
        self.execute('test.limits.model', 'consume_nothing')

class BenchLogin(Bench):
    """Login (update res_users.date)."""

    command_name = 'bench-login'
    bench_name = 'res.users.login(1)'

    def measure_once(self, i):
        self.common_proxy.login(self.database, self.user, self.password)
