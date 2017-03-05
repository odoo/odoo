odoo.define('web.pyEval_tests', function(require) {
"use strict";

var data = require('web.data');
var pyEval = require('web.pyeval');
var time = require('web.time');

QUnit.module('core', function () {

    QUnit.module('PY.eval');

    QUnit.test('simple python expression', function(assert) {
        assert.expect(2);

        var result = pyEval.py_eval("True and False");
        assert.strictEqual(result, false, "should properly evaluate basic expression");
        result = pyEval.py_eval("a + b", {a: 1, b: 41});
        assert.strictEqual(result, 42, "should properly evaluate basic sum");
    });

    QUnit.test('not prefix', function (assert) {
        assert.expect(3);

        assert.ok(py.eval('not False'));
        assert.ok(py.eval('not foo', {foo: false}));
        assert.ok(py.eval('not a in b', {a: 3, b: [1, 2, 4, 8]}));
    });


    function makeTimeCheck (assert) {
        var context = pyEval.context();
        return function (expr, func, message) {
            // evaluate expr between two calls to new Date(), and check that
            // the result is between the transformed dates
            var d0 = new Date();
            var result = py.eval(expr, context);
            var d1 = new Date();
            assert.ok(func(d0) <= result && result <= func(d1), message);
        };
    }

    // Port from pypy/lib_pypy/test_datetime.py
    function makeEq(assert, c2) {
        var ctx = pyEval.context();
        var c = _.extend({ td: ctx.datetime.timedelta }, c2 || {});
        return function (a, b, message) {
            assert.ok(py.eval(a + ' == ' + b, c), message);
        };
    };

    QUnit.test('strftime', function (assert) {
        assert.expect(3);

        var check = makeTimeCheck(assert);

        check("time.strftime('%Y')", function(d) {
            return String(d.getFullYear());
        });

        check("time.strftime('%Y')+'-01-30'", function(d) {
            return String(d.getFullYear()) + '-01-30';
        });

        check("time.strftime('%Y-%m-%d %H:%M:%S')", function(d) {
            return _.str.sprintf('%04d-%02d-%02d %02d:%02d:%02d',
                d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate(),
                d.getUTCHours(), d.getUTCMinutes(), d.getUTCSeconds());
        });
    });

    QUnit.test('context_today', function (assert) {
        assert.expect(1);

        var check = makeTimeCheck(assert, pyEval);

        check("context_today().strftime('%Y-%m-%d')", function(d) {
            return String(_.str.sprintf('%04d-%02d-%02d',
                d.getFullYear(), d.getMonth() + 1, d.getDate()));
        });
    });

    QUnit.test('timedelta.test_constructor', function (assert) {
        assert.expect(16);

        var eq = makeEq(assert);

        // keyword args to constructor
        eq('td()', 'td(weeks=0, days=0, hours=0, minutes=0, seconds=0, ' +
                        'milliseconds=0, microseconds=0)');
        eq('td(1)', 'td(days=1)');
        eq('td(0, 1)', 'td(seconds=1)');
        eq('td(0, 0, 1)', 'td(microseconds=1)');
        eq('td(weeks=1)', 'td(days=7)');
        eq('td(days=1)', 'td(hours=24)');
        eq('td(hours=1)', 'td(minutes=60)');
        eq('td(minutes=1)', 'td(seconds=60)');
        eq('td(seconds=1)', 'td(milliseconds=1000)');
        eq('td(milliseconds=1)', 'td(microseconds=1000)');

        // Check float args to constructor
        eq('td(weeks=1.0/7)', 'td(days=1)');
        eq('td(days=1.0/24)', 'td(hours=1)');
        eq('td(hours=1.0/60)', 'td(minutes=1)');
        eq('td(minutes=1.0/60)', 'td(seconds=1)');
        eq('td(seconds=0.001)', 'td(milliseconds=1)');
        eq('td(milliseconds=0.001)', 'td(microseconds=1)');
    });

    QUnit.test('timedelta.test_computations', function (assert) {
        assert.expect(28);

        var c = pyEval.context();
        var zero = py.float.fromJSON(0);
        var eq = makeEq(assert, {
            // one week
            a: py.PY_call(c.datetime.timedelta, [
                py.float.fromJSON(7)]),
            // one minute
            b: py.PY_call(c.datetime.timedelta, [
                zero, py.float.fromJSON(60)]),
            // one millisecond
            c: py.PY_call(c.datetime.timedelta, [
                zero, zero, py.float.fromJSON(1000)]),
        });

        eq('a+b+c', 'td(7, 60, 1000)');
        eq('a-b', 'td(6, 24*3600 - 60)');
        eq('-a', 'td(-7)');
        eq('+a', 'td(7)');
        eq('-b', 'td(-1, 24*3600 - 60)');
        eq('-c', 'td(-1, 24*3600 - 1, 999000)');
        // eq('abs(a)', 'a');
        // eq('abs(-a)', 'a');
        eq('td(6, 24*3600)', 'a');
        eq('td(0, 0, 60*1000000)', 'b');
        eq('a*10', 'td(70)');
        eq('a*10', '10*a');
        // eq('a*10L', '10*a');
        eq('b*10', 'td(0, 600)');
        eq('10*b', 'td(0, 600)');
        // eq('b*10L', 'td(0, 600)');
        eq('c*10', 'td(0, 0, 10000)');
        eq('10*c', 'td(0, 0, 10000)');
        // eq('c*10L', 'td(0, 0, 10000)');
        eq('a*-1', '-a');
        eq('b*-2', '-b-b');
        eq('c*-2', '-c+-c');
        eq('b*(60*24)', '(b*60)*24');
        eq('b*(60*24)', '(60*b)*24');
        eq('c*1000', 'td(0, 1)');
        eq('1000*c', 'td(0, 1)');
        eq('a//7', 'td(1)');
        eq('b//10', 'td(0, 6)');
        eq('c//1000', 'td(0, 0, 1)');
        eq('a//10', 'td(0, 7*24*360)');
        eq('a//3600000', 'td(0, 0, 7*24*1000)');

        // Issue #11576
        eq('td(999999999, 86399, 999999) - td(999999999, 86399, 999998)', 'td(0, 0, 1)');
        eq('td(999999999, 1, 1) - td(999999999, 1, 0)',
            'td(0, 0, 1)');
    });

    QUnit.test('timedelta.test_basic_attributes', function (assert) {
        assert.expect(3);

        var ctx = pyEval.context();
        assert.strictEqual(py.eval('datetime.timedelta(1, 7, 31).days', ctx), 1);
        assert.strictEqual(py.eval('datetime.timedelta(1, 7, 31).seconds', ctx), 7);
        assert.strictEqual(py.eval('datetime.timedelta(1, 7, 31).microseconds', ctx), 31);
    });

    QUnit.test('timedelta.test_total_seconds', function (assert) {
        assert.expect(6);

        var c = { timedelta: pyEval.context().datetime.timedelta };
        assert.strictEqual(py.eval('timedelta(365).total_seconds()', c), 31536000);
        assert.strictEqual(
            py.eval('timedelta(seconds=123456.789012).total_seconds()', c),
            123456.789012);
        assert.strictEqual(
            py.eval('timedelta(seconds=-123456.789012).total_seconds()', c),
            -123456.789012);
        assert.strictEqual(
            py.eval('timedelta(seconds=0.123456).total_seconds()', c), 0.123456);
        assert.strictEqual(py.eval('timedelta().total_seconds()', c), 0);
        assert.strictEqual(
            py.eval('timedelta(seconds=1000000).total_seconds()', c), 1e6);
    });

    QUnit.test('timedelta.test_str', function (assert) {
        assert.expect(10);

        var c = { td: pyEval.context().datetime.timedelta };

        assert.strictEqual(py.eval('str(td(1))', c), "1 day, 0:00:00");
        assert.strictEqual(py.eval('str(td(-1))', c), "-1 day, 0:00:00");
        assert.strictEqual(py.eval('str(td(2))', c), "2 days, 0:00:00");
        assert.strictEqual(py.eval('str(td(-2))', c), "-2 days, 0:00:00");

        assert.strictEqual(py.eval('str(td(hours=12, minutes=58, seconds=59))', c),
                    "12:58:59");
        assert.strictEqual(py.eval('str(td(hours=2, minutes=3, seconds=4))', c),
                        "2:03:04");
        assert.strictEqual(
            py.eval('str(td(weeks=-30, hours=23, minutes=12, seconds=34))', c),
            "-210 days, 23:12:34");

        assert.strictEqual(py.eval('str(td(milliseconds=1))', c), "0:00:00.001000");
        assert.strictEqual(py.eval('str(td(microseconds=3))', c), "0:00:00.000003");

        assert.strictEqual(
            py.eval('str(td(days=999999999, hours=23, minutes=59, seconds=59, microseconds=999999))', c),
            "999999999 days, 23:59:59.999999");
    });

    QUnit.test('timedelta.test_massive_normalization', function (assert) {
        assert.expect(3);

        var td = py.PY_call(
            pyEval.context().datetime.timedelta,
            {microseconds: py.float.fromJSON(-1)});
        assert.strictEqual(td.days, -1);
        assert.strictEqual(td.seconds, 24 * 3600 - 1);
        assert.strictEqual(td.microseconds, 999999);
    });

    QUnit.test('timedelta.test_bool', function (assert) {
        assert.expect(5);

        var c = { td: pyEval.context().datetime.timedelta };
        assert.ok(py.eval('bool(td(1))', c));
        assert.ok(py.eval('bool(td(0, 1))', c));
        assert.ok(py.eval('bool(td(0, 0, 1))', c));
        assert.ok(py.eval('bool(td(microseconds=1))', c));
        assert.ok(py.eval('bool(not td(0))', c));
    });

    QUnit.test('date.test_computations', function (assert) {
        assert.expect(31);

        var d = pyEval.context().datetime;

        var a = d.date.fromJSON(2002, 1, 31);
        var b = d.date.fromJSON(1956, 1, 31);
        assert.strictEqual(
            py.eval('(a - b).days', {a: a, b: b}),
            46 * 365 + 12);
        assert.strictEqual(py.eval('(a - b).seconds', {a: a, b: b}), 0);
        assert.strictEqual(py.eval('(a - b).microseconds', {a: a, b: b}), 0);

        var day = py.PY_call(d.timedelta, [py.float.fromJSON(1)]);
        var week = py.PY_call(d.timedelta, [py.float.fromJSON(7)]);
        a = d.date.fromJSON(2002, 3, 2);
        var ctx = {
            a: a,
            day: day,
            week: week,
            date: d.date
        };
        assert.ok(py.eval('a + day == date(2002, 3, 3)', ctx));
        assert.ok(py.eval('day + a == date(2002, 3, 3)', ctx)); // 5
        assert.ok(py.eval('a - day == date(2002, 3, 1)', ctx));
        assert.ok(py.eval('-day + a == date(2002, 3, 1)', ctx));
        assert.ok(py.eval('a + week == date(2002, 3, 9)', ctx));
        assert.ok(py.eval('a - week == date(2002, 2, 23)', ctx));
        assert.ok(py.eval('a + 52*week == date(2003, 3, 1)', ctx)); // 10
        assert.ok(py.eval('a - 52*week == date(2001, 3, 3)', ctx));
        assert.ok(py.eval('(a + week) - a == week', ctx));
        assert.ok(py.eval('(a + day) - a == day', ctx));
        assert.ok(py.eval('(a - week) - a == -week', ctx));
        assert.ok(py.eval('(a - day) - a == -day', ctx)); // 15
        assert.ok(py.eval('a - (a + week) == -week', ctx));
        assert.ok(py.eval('a - (a + day) == -day', ctx));
        assert.ok(py.eval('a - (a - week) == week', ctx));
        assert.ok(py.eval('a - (a - day) == day', ctx));

        assert.throws(function () {
            py.eval('a + 1', ctx);
        }, /^Error: TypeError:/); //20
        assert.throws(function () {
            py.eval('a - 1', ctx);
        }, /^Error: TypeError:/); 
        assert.throws(function () {
            py.eval('1 + a', ctx);
        }, /^Error: TypeError:/); 
        assert.throws(function () {
            py.eval('1 - a', ctx);
        }, /^Error: TypeError:/); 

        // delta - date is senseless.
        assert.throws(function () {
            py.eval('day - a', ctx);
        }, /^Error: TypeError:/);
        // mixing date and (delta or date) via * or // is senseless
        assert.throws(function () {
            py.eval('day * a', ctx);
        }, /^Error: TypeError:/); // 25
        assert.throws(function () {
            py.eval('a * day', ctx);
        }, /^Error: TypeError:/);
        assert.throws(function () {
            py.eval('day // a', ctx);
        }, /^Error: TypeError:/);
        assert.throws(function () {
            py.eval('a // day', ctx);
        }, /^Error: TypeError:/);
        assert.throws(function () {
            py.eval('a * a', ctx);
        }, /^Error: TypeError:/);
        assert.throws(function () {
            py.eval('a // a', ctx);
        }, /^Error: TypeError:/); // 30
        // date + date is senseless
        assert.throws(function () {
            py.eval('a + a', ctx);
        }, /^Error: TypeError:/);

    });

    QUnit.test('relativedelta', function (assert) {
        assert.expect(5);

        assert.strictEqual(
            py.eval("(datetime.date(2012, 2, 15) + relativedelta(days=-1)).strftime('%Y-%m-%d 23:59:59')",
                    pyEval.context()),
            "2012-02-14 23:59:59");
        assert.strictEqual(
            py.eval("(datetime.date(2012, 2, 15) + relativedelta(days=1)).strftime('%Y-%m-%d')",
                    pyEval.context()),
            "2012-02-16");
        assert.strictEqual(
            py.eval("(datetime.date(2012, 2, 15) + relativedelta(days=-1)).strftime('%Y-%m-%d')",
                    pyEval.context()),
            "2012-02-14");
        assert.strictEqual(
            py.eval("(datetime.date(2012, 2, 1) + relativedelta(days=-1)).strftime('%Y-%m-%d')",
                    pyEval.context()),
            '2012-01-31');
        assert.strictEqual(
            py.eval("(datetime.date(2015,2,5)+relativedelta(days=-6,weekday=0)).strftime('%Y-%m-%d')",
                    pyEval.context()),
            '2015-02-02');
    });

    QUnit.test('datetime.tojson', function (assert) {
        assert.expect(7);

        var result = py.eval(
            'datetime.datetime(2012, 2, 15, 1, 7, 31)',
            pyEval.context());

        assert.ok(result instanceof Date);
        assert.strictEqual(result.getFullYear(), 2012);
        assert.strictEqual(result.getMonth(), 1);
        assert.strictEqual(result.getDate(), 15);
        assert.strictEqual(result.getHours(), 1);
        assert.strictEqual(result.getMinutes(), 7);
        assert.strictEqual(result.getSeconds(), 31);
    });

    QUnit.test('datetime.combine', function (assert) {
        assert.expect(2);

        var result = py.eval(
            'datetime.datetime.combine(datetime.date(2012, 2, 15),' +
            '                          datetime.time(1, 7, 13))' +
            '   .strftime("%Y-%m-%d %H:%M:%S")',
            pyEval.context());
        assert.strictEqual(result, "2012-02-15 01:07:13");

        result = py.eval(
            'datetime.datetime.combine(datetime.date(2012, 2, 15),' +
            '                          datetime.time())' +
            '   .strftime("%Y-%m-%d %H:%M:%S")',
            pyEval.context());
        assert.strictEqual(result, '2012-02-15 00:00:00');
    });

    QUnit.test('datetime.replace', function (assert) {
        assert.expect(1);

        var result = py.eval(
            'datetime.datetime(2012, 2, 15, 1, 7, 13)' +
            '   .replace(hour=0, minute=0, second=0)' +
            '   .strftime("%Y-%m-%d %H:%M:%S")',
            pyEval.context());
        assert.strictEqual(result, "2012-02-15 00:00:00");
    });

    QUnit.module('pyeval (eval domain contexts)', {
        beforeEach: function() {
            this.user_context = {
                uid: 1,
                lang: 'en_US',
                tz: false,
            };
        },
    });


    QUnit.test('empty, basic', function (assert) {
        assert.expect(3);

        var result = pyEval.eval_domains_and_contexts({
            contexts: [this.user_context],
            domains: [],
        });

        // default values for new db
        assert.deepEqual(result.context, {
            lang: 'en_US',
            tz: false,
            uid: 1
        });
        assert.deepEqual(result.domain, []);
        assert.deepEqual(result.group_by, []);
    });


    QUnit.test('context_merge_00', function (assert) {
        assert.expect(1);

        var ctx = [
            {
                "__contexts": [
                    { "lang": "en_US", "tz": false, "uid": 1 },
                    {
                        "active_id": 8,
                        "active_ids": [ 8 ],
                        "active_model": "sale.order",
                        "bin_raw": true,
                        "default_composition_mode": "comment",
                        "default_model": "sale.order",
                        "default_res_id": 8,
                        "default_template_id": 18,
                        "default_use_template": true,
                        "edi_web_url_view": "faaaake",
                        "lang": "en_US",
                        "mark_so_as_sent": null,
                        "show_address": null,
                        "tz": false,
                        "uid": null
                    },
                    {}
                ],
                "__eval_context": null,
                "__ref": "compound_context"
            },
            { "active_id": 9, "active_ids": [ 9 ], "active_model": "mail.compose.message" }
        ];
        var result = pyEval.eval_domains_and_contexts({
            contexts: ctx, 
            domins: [],
        });

        assert.deepEqual(result.context, {
            active_id: 9,
            active_ids: [9],
            active_model: 'mail.compose.message',
            bin_raw: true,
            default_composition_mode: 'comment',
            default_model: 'sale.order',
            default_res_id: 8,
            default_template_id: 18,
            default_use_template: true,
            edi_web_url_view: "faaaake",
            lang: 'en_US',
            mark_so_as_sent: null,
            show_address: null,
            tz: false,
            uid: null
        });

    });

    QUnit.test('context_merge_01', function (assert) {
        assert.expect(1);

        var ctx = [{
            "__contexts": [
                {
                    "lang": "en_US",
                    "tz": false,
                    "uid": 1
                },
                {
                    "default_attachment_ids": [],
                    "default_body": "",
                    "default_content_subtype": "html",
                    "default_model": "res.users",
                    "default_parent_id": false,
                    "default_res_id": 1
                },
                {}
            ],
            "__eval_context": null,
            "__ref": "compound_context"
        }];
        var result = pyEval.eval_domains_and_contexts({
            contexts: ctx,
            domains: [],
        });

        assert.deepEqual(result.context, {
            "default_attachment_ids": [],
            "default_body": "",
            "default_content_subtype": "html",
            "default_model": "res.users",
            "default_parent_id": false,
            "default_res_id": 1,
            "lang": "en_US",
            "tz": false,
            "uid": 1
        });
    });

    QUnit.test('domain with time', function (assert) {
        assert.expect(1);

        var result = pyEval.eval_domains_and_contexts({
            domains: [
                [['type', '=', 'contract']],
                { "__domains": [["|"], [["state", "in", ["open", "draft"]]], [["type", "=", "contract"], ["state", "=", "pending"]]],
                  "__eval_context": null,
                  "__ref": "compound_domain"
                },
                "['|', '&', ('date', '!=', False), ('date', '<=', time.strftime('%Y-%m-%d')), ('is_overdue_quantity', '=', True)]",
                [['user_id', '=', 1]]
            ],
            contexts: [],
        });

        var d = new Date();
        var today = _.str.sprintf("%04d-%02d-%02d",
                d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate());
        assert.deepEqual(result.domain, [
            ["type", "=", "contract"],
            "|", ["state", "in", ["open", "draft"]],
                "&", ["type", "=", "contract"],
                     ["state", "=", "pending"],
            "|",
                "&", ["date", "!=", false],
                        ["date", "<=", today],
                ["is_overdue_quantity", "=", true],
            ["user_id", "=", 1]
        ]);
    });

    QUnit.test('conditional context', function (assert) {
        assert.expect(2);

        var d = {
            __ref: 'domain',
            __debug: "[('company_id', '=', context.get('company_id',False))]"
        };

        var result1 = pyEval.eval_domains_and_contexts({
            domains: [d],
            contexts: [],
        });
        assert.deepEqual(result1.domain, [['company_id', '=', false]]);

        var compound_domain = new data.CompoundDomain(d);
        compound_domain.set_eval_context({company_id: 42});

        var result2 = pyEval.eval_domains_and_contexts({
            domains: [compound_domain],
            contexts: [],
        });

        assert.deepEqual(result2.domain, [['company_id', '=', 42]]);
    });

    QUnit.test('substitution in context', function (assert) {
        assert.expect(1);

        // setup(session);
        var c = "{'default_opportunity_id': active_id, 'default_duration': 1.0, 'lng': lang}";
        var cc = new data.CompoundContext(c);
        cc.set_eval_context({active_id: 42});
        var result = pyEval.eval_domains_and_contexts({
            domains:[], contexts: [this.user_context, cc]
        });

        assert.deepEqual(result.context, {
            lang: "en_US",
            tz: false,
            uid: 1,
            default_opportunity_id: 42,
            default_duration: 1.0,
            lng: "en_US"
        });
    });

    QUnit.test('date', function (assert) {
        assert.expect(1);

        var d = "[('state','!=','cancel'),('opening_date','>',context_today().strftime('%Y-%m-%d'))]";
        var result = pyEval.eval_domains_and_contexts({
            domains: [d],
            contexts: [],
        });

        var date = new Date();
        var today = _.str.sprintf("%04d-%02d-%02d",
            date.getFullYear(), date.getMonth() + 1, date.getDate());
        assert.deepEqual(result.domain, [
            ['state', '!=', 'cancel'],
            ['opening_date', '>', today]
        ]);
    });

    QUnit.test('delta', function (assert) {
        assert.expect(1);

        var d = "[('type','=','in'),('day','<=', time.strftime('%Y-%m-%d')),('day','>',(context_today()-datetime.timedelta(days=15)).strftime('%Y-%m-%d'))]";
        var result = pyEval.eval_domains_and_contexts({
            domains: [d],
            contexts: [],
        });
        var date = new Date();
        var today = _.str.sprintf("%04d-%02d-%02d",
            date.getFullYear(), date.getMonth() + 1, date.getDate());
        date.setDate(date.getDate() - 15);
        var ago_15_d = _.str.sprintf("%04d-%02d-%02d",
            date.getFullYear(), date.getMonth() + 1, date.getDate());
        assert.deepEqual(result.domain, [
            ['type', '=', 'in'],
            ['day', '<=', today],
            ['day', '>', ago_15_d]
        ]);
    });

    QUnit.test('horror from the deep', function (assert) {
        assert.expect(1);

        var cs = [
            {"__ref": "compound_context",
                "__contexts": [
                    {"__ref": "context", "__debug": "{'k': 'foo,' + str(context.get('test_key', False))}"},
                    {"__ref": "compound_context",
                        "__contexts": [
                            {"lang": "en_US", "tz": false, "uid": 1},
                            {"lang": "en_US", "tz": false, "uid": 1,
                                "active_model": "sale.order", "default_type": "out",
                                "show_address": 1, "contact_display": "partner_address",
                                "active_ids": [9], "active_id": 9},
                            {}
                        ], "__eval_context": null },
                    {"active_id": 8, "active_ids": [8],
                        "active_model": "stock.picking.out"},
                    {"__ref": "context", "__debug": "{'default_ref': 'stock.picking.out,'+str(context.get('active_id', False))}", "__id": "54d6ad1d6c45"}
                ], "__eval_context": null}
        ];
        var result = pyEval.eval_domains_and_contexts({
            domains: [],
            contexts: cs,
        });

        assert.deepEqual(result.context, {
            k: 'foo,False',
            lang: 'en_US',
            tz: false,
            uid: 1,
            active_model: 'stock.picking.out',
            active_id: 8,
            active_ids: [8],
            default_type: 'out',
            show_address: 1,
            contact_display: 'partner_address',
            default_ref: 'stock.picking.out,8'
        });
    });

    QUnit.module('pyeval (contexts)');

    QUnit.test('context_recursive', function (assert) {
        assert.expect(3);

        var context_to_eval = [{
            __ref: 'context',
            __debug: '{"foo": context.get("bar", "qux")}'
        }];
        assert.deepEqual(
            pyEval.eval('contexts', context_to_eval, {bar: "ok"}),
            {foo: 'ok'});
        assert.deepEqual(
            pyEval.eval('contexts', context_to_eval, {bar: false}),
            {foo: false});
        assert.deepEqual(
            pyEval.eval('contexts', context_to_eval),
            {foo: 'qux'});
    });

    QUnit.test('context_sequences', function (assert) {
        assert.expect(1);

        // Context n should have base evaluation context + all of contexts
        // 0..n-1 in its own evaluation context
        var active_id = 4;
        var result = pyEval.eval('contexts', [
            {
                "__contexts": [
                    {
                        "department_id": false,
                        "lang": "en_US",
                        "project_id": false,
                        "section_id": false,
                        "tz": false,
                        "uid": 1
                    },
                    { "search_default_create_uid": 1 },
                    {}
                ],
                "__eval_context": null,
                "__ref": "compound_context"
            },
            {
                "active_id": active_id,
                "active_ids": [ active_id ],
                "active_model": "purchase.requisition"
            },
            {
                "__debug": "{'record_id' : active_id}",
                "__id": "63e8e9bff8a6",
                "__ref": "context"
            }
        ]);

        assert.deepEqual(result, {
            department_id: false,
            lang: 'en_US',
            project_id: false,
            section_id: false,
            tz: false,
            uid: 1,
            search_default_create_uid: 1,
            active_id: active_id,
            active_ids: [active_id],
            active_model: 'purchase.requisition',
            record_id: active_id
        });
    });

    QUnit.test('non-literal_eval_contexts', function (assert) {
        assert.expect(1);

        var result = pyEval.eval('contexts', [{
            "__ref": "compound_context",
            "__contexts": [
                {"__ref": "context", "__debug": "{'type':parent.type}",
                    "__id": "462b9dbed42f"}
            ],
            "__eval_context": {
                "__ref": "compound_context",
                "__contexts": [{
                        "__ref": "compound_context",
                        "__contexts": [
                            {"__ref": "context", "__debug": "{'type': type}",
                                "__id": "16a04ed5a194"}
                        ],
                        "__eval_context": {
                            "__ref": "compound_context",
                            "__contexts": [
                                {"lang": "en_US", "tz": false, "uid": 1,
                                    "journal_type": "sale", "section_id": false,
                                    "default_type": "out_invoice",
                                    "type": "out_invoice", "department_id": false},
                                {"id": false, "journal_id": 10,
                                    "number": false, "type": "out_invoice",
                                    "currency_id": 1, "partner_id": 4,
                                    "fiscal_position_id": false,
                                    "date_invoice": false, "date": false,
                                    "payment_term_id": false, "reference_type": "none",
                                    "reference": false, "account_id": 440,
                                    "name": false, "invoice_line_ids": [],
                                    "tax_line_ids": [], "amount_untaxed": 0,
                                    "amount_tax": 0, "reconciled": false,
                                    "amount_total": 0, "state": "draft",
                                    "residual": 0, "company_id": 1,
                                    "date_due": false, "user_id": 1,
                                    "partner_bank_id": false, "origin": false,
                                    "move_id": false, "comment": false,
                                    "payment_ids": [[6, false, []]],
                                    "active_id": false, "active_ids": [],
                                    "active_model": "account.invoice",
                                    "parent": {}}
                    ], "__eval_context": null}
                }, {
                    "id": false,
                    "product_id": 4,
                    "name": "[PC1] Basic PC",
                    "quantity": 1,
                    "uom_id": 1,
                    "price_unit": 100,
                    "account_id": 853,
                    "discount": 0,
                    "account_analytic_id": false,
                    "company_id": false,
                    "note": false,
                    "invoice_line_tax_ids": [[6, false, [1]]],
                    "active_id": false,
                    "active_ids": [],
                    "active_model": "account.invoice.line",
                    "parent": {
                        "id": false, "journal_id": 10, "number": false,
                        "type": "out_invoice", "currency_id": 1,
                        "partner_id": 4, "fiscal_position_id": false,
                        "date_invoice": false, "date": false,
                        "payment_term_id": false, "reference_type": "none",
                        "reference": false, "account_id": 440, "name": false,
                        "tax_line_ids": [], "amount_untaxed": 0, "amount_tax": 0,
                        "reconciled": false, "amount_total": 0,
                        "state": "draft", "residual": 0, "company_id": 1,
                        "date_due": false, "user_id": 1,
                        "partner_bank_id": false, "origin": false,
                        "move_id": false, "comment": false,
                        "payment_ids": [[6, false, []]]}
                }],
                "__eval_context": null
            }
        }]);

        assert.deepEqual(result, {type: 'out_invoice'});
    });

    QUnit.test('return-input-value', function (assert) {
        assert.expect(1);

        var result = pyEval.eval('contexts', [{
            __ref: 'compound_context',
            __contexts: ["{'line_id': line_id , 'journal_id': journal_id }"],
            __eval_context: {
                __ref: 'compound_context',
                __contexts: [{
                    __ref: 'compound_context',
                    __contexts: [
                        {lang: 'en_US', tz: 'Europe/Paris', uid: 1},
                        {lang: 'en_US', tz: 'Europe/Paris', uid: 1},
                        {}
                    ],
                    __eval_context: null,
                }, {
                    active_id: false,
                    active_ids: [],
                    active_model: 'account.move',
                    amount: 0,
                    company_id: 1,
                    id: false,
                    journal_id: 14,
                    line_id: [
                        [0, false, {
                            account_id: 55,
                            amount_currency: 0,
                            analytic_account_id: false,
                            credit: 0,
                            currency_id: false,
                            date_maturity: false,
                            debit: 0,
                            name: "dscsd",
                            partner_id: false,
                            tax_line_id: false,
                        }]
                    ],
                    name: '/',
                    narration: false,
                    parent: {},
                    partner_id: false,
                    date: '2011-01-1',
                    ref: false,
                    state: 'draft',
                    to_check: false,
                }],
                __eval_context: null,
            },
        }]);
        assert.deepEqual(result, {
            journal_id: 14,
            line_id: [[0, false, {
                account_id: 55,
                amount_currency: 0,
                analytic_account_id: false,
                credit: 0,
                currency_id: false,
                date_maturity: false,
                debit: 0,
                name: "dscsd",
                partner_id: false,
                tax_line_id: false,
            }]],
        });
    });

    QUnit.module('pyeval (domains)');

    QUnit.test('current_date', function (assert) {
        assert.expect(1);

        var current_date = time.date_to_str(new Date());
        var result = pyEval.eval('domains',
            [[],{"__ref":"domain","__debug":"[('name','>=',current_date),('name','<=',current_date)]","__id":"5dedcfc96648"}],
            pyEval.context());
        assert.deepEqual(result, [
            ['name', '>=', current_date],
            ['name', '<=', current_date]
        ]);
    });

    QUnit.test('context_freevar', function (assert) {
        assert.expect(3);

        var domains_to_eval = [{
            __ref: 'domain',
            __debug: '[("foo", "=", context.get("bar", "qux"))]'
        }, [['bar', '>=', 42]]];
        assert.deepEqual(
            pyEval.eval('domains', domains_to_eval, {bar: "ok"}),
            [['foo', '=', 'ok'], ['bar', '>=', 42]]);
        assert.deepEqual(
            pyEval.eval('domains', domains_to_eval, {bar: false}),
            [['foo', '=', false], ['bar', '>=', 42]]);
        assert.deepEqual(
            pyEval.eval('domains', domains_to_eval),
            [['foo', '=', 'qux'], ['bar', '>=', 42]]);
    });

    QUnit.module('pyeval (groupbys)');

    QUnit.test('groupbys_00', function (assert) {
        assert.expect(1);

        var result = pyEval.eval('groupbys', [
            {group_by: 'foo'},
            {group_by: ['bar', 'qux']},
            {group_by: null},
            {group_by: 'grault'}
        ]);
        assert.deepEqual(result, ['foo', 'bar', 'qux', 'grault']);
    });

    QUnit.test('groupbys_01', function (assert) {
        assert.expect(1);

        var result = pyEval.eval('groupbys', [
            {group_by: 'foo'},
            { __ref: 'context', __debug: '{"group_by": "bar"}' },
            {group_by: 'grault'}
        ]);
        assert.deepEqual(result, ['foo', 'bar', 'grault']);
    });

    QUnit.test('groupbys_02', function (assert) {
        assert.expect(1);

        var result = pyEval.eval('groupbys', [
            {group_by: 'foo'},
            {
                __ref: 'compound_context',
                __contexts: [ {group_by: 'bar'} ],
                __eval_context: null
            },
            {group_by: 'grault'}
        ]);
        assert.deepEqual(result, ['foo', 'bar', 'grault']);
    });

    QUnit.test('groupbys_03', function (assert) {
        assert.expect(1);

        var result = pyEval.eval('groupbys', [
            {group_by: 'foo'},
            {
                __ref: 'compound_context',
                __contexts: [
                    { __ref: 'context', __debug: '{"group_by": value}' }
                ],
                __eval_context: { value: 'bar' }
            },
            {group_by: 'grault'}
        ]);
        assert.deepEqual(result, ['foo', 'bar', 'grault']);
    });

    QUnit.test('groupbys_04', function (assert) {
        assert.expect(1);

        var result = pyEval.eval('groupbys', [
            {group_by: 'foo'},
            {
                __ref: 'compound_context',
                __contexts: [
                    { __ref: 'context', __debug: '{"group_by": value}' }
                ],
                __eval_context: { value: 'bar' }
            },
            {group_by: 'grault'}
        ], { value: 'bar' });
        assert.deepEqual(result, ['foo', 'bar', 'grault']);
    });

    QUnit.test('groupbys_05', function (assert) {
        assert.expect(1);

        var result = pyEval.eval('groupbys', [
            {group_by: 'foo'},
            { __ref: 'context', __debug: '{"group_by": value}' },
            {group_by: 'grault'}
        ], { value: 'bar' });
        assert.deepEqual(result, ['foo', 'bar', 'grault']);
    });

});

});

