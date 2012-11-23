openerp.testing.section('eval.types', {
    dependencies: ['web.coresetup'],
    setup: function (instance) {
        instance.session.uid = 42;
    }
}, function (test) {
    test('strftime', function (instance) {
        var d = new Date();
        var context = instance.web.pyeval.context();
        strictEqual(
            py.eval("time.strftime('%Y')", context),
            String(d.getFullYear()));
        strictEqual(
            py.eval("time.strftime('%Y')+'-01-30'", context),
            String(d.getFullYear()) + '-01-30');
        strictEqual(
            py.eval("time.strftime('%Y-%m-%d %H:%M:%S')", context),
            _.str.sprintf('%04d-%02d-%02d %02d:%02d:%02d',
                d.getFullYear(), d.getMonth() + 1, d.getDate(),
                d.getHours(), d.getMinutes(), d.getSeconds()));
    });
    // Port from pypy/lib_pypy/test_datetime.py
    var makeEq = function (instance, c2) {
        var ctx = instance.web.pyeval.context();
        var c = _.extend({ td: ctx.datetime.timedelta }, c2 || {});
        return function (a, b, message) {
            ok(py.eval(a + ' == ' + b, c), message);
        };
    };
    test('timedelta.test_constructor', function (instance) {
        var eq = makeEq(instance);

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
    test('timedelta.test_computations', function (instance) {
        var c = instance.web.pyeval.context();
        var zero = py.float.fromJSON(0);
        var eq = makeEq(instance, {
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
//        eq('abs(a)', 'a');
//        eq('abs(-a)', 'a');
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
           'td(0, 0, 1)')
    });
    test('timedelta.test_basic_attributes', function (instance) {
        var ctx = instance.web.pyeval.context();
        strictEqual(py.eval('datetime.timedelta(1, 7, 31).days', ctx), 1);
        strictEqual(py.eval('datetime.timedelta(1, 7, 31).seconds', ctx), 7);
        strictEqual(py.eval('datetime.timedelta(1, 7, 31).microseconds', ctx), 31);
    });
    test('timedelta.test_total_seconds', function (instance) {
        var c = { timedelta: instance.web.pyeval.context().datetime.timedelta };
        strictEqual(py.eval('timedelta(365).total_seconds()', c), 31536000);
        strictEqual(
            py.eval('timedelta(seconds=123456.789012).total_seconds()', c),
            123456.789012);
        strictEqual(
            py.eval('timedelta(seconds=-123456.789012).total_seconds()', c),
            -123456.789012);
        strictEqual(
            py.eval('timedelta(seconds=0.123456).total_seconds()', c), 0.123456);
        strictEqual(py.eval('timedelta().total_seconds()', c), 0);
        strictEqual(
            py.eval('timedelta(seconds=1000000).total_seconds()', c), 1e6);
    });
    test('timedelta.test_str', function (instance) {
        var c = { td: instance.web.pyeval.context().datetime.timedelta };

        strictEqual(py.eval('str(td(1))', c), "1 day, 0:00:00");
        strictEqual(py.eval('str(td(-1))', c), "-1 day, 0:00:00");
        strictEqual(py.eval('str(td(2))', c), "2 days, 0:00:00");
        strictEqual(py.eval('str(td(-2))', c), "-2 days, 0:00:00");

        strictEqual(py.eval('str(td(hours=12, minutes=58, seconds=59))', c),
                    "12:58:59");
        strictEqual(py.eval('str(td(hours=2, minutes=3, seconds=4))', c),
                     "2:03:04");
        strictEqual(
            py.eval('str(td(weeks=-30, hours=23, minutes=12, seconds=34))', c),
            "-210 days, 23:12:34");

        strictEqual(py.eval('str(td(milliseconds=1))', c), "0:00:00.001000");
        strictEqual(py.eval('str(td(microseconds=3))', c), "0:00:00.000003");

        strictEqual(
            py.eval('str(td(days=999999999, hours=23, minutes=59, seconds=59, microseconds=999999))', c),
           "999999999 days, 23:59:59.999999");
    });
    test('timedelta.test_massive_normalization', function (instance) {
        var td = py.PY_call(
            instance.web.pyeval.context().datetime.timedelta,
            {microseconds: py.float.fromJSON(-1)});
        strictEqual(td.days, -1);
        strictEqual(td.seconds, 24 * 3600 - 1);
        strictEqual(td.microseconds, 999999);
    });
    test('timedelta.test_bool', function (instance) {
        var c = { td: instance.web.pyeval.context().datetime.timedelta };
        ok(py.eval('bool(td(1))', c));
        ok(py.eval('bool(td(0, 1))', c));
        ok(py.eval('bool(td(0, 0, 1))', c));
        ok(py.eval('bool(td(microseconds=1))', c));
        ok(py.eval('bool(not td(0))', c));
    });

    test('date.test_computations', function (instance) {
        var d = instance.web.pyeval.context().datetime;

        var a = d.date.fromJSON(2002, 1, 31);
        var b = d.date.fromJSON(1956, 1, 31);
        strictEqual(
            py.eval('(a - b).days', {a: a, b: b}),
            46 * 365 + 12);
        strictEqual(py.eval('(a - b).seconds', {a: a, b: b}), 0);
        strictEqual(py.eval('(a - b).microseconds', {a: a, b: b}), 0);

        var day = py.PY_call(d.timedelta, [py.float.fromJSON(1)]);
        var week = py.PY_call(d.timedelta, [py.float.fromJSON(7)]);
        a = d.date.fromJSON(2002, 3, 2);
        var ctx = {
            a: a,
            day: day,
            week: week,
            date: d.date
        };
        ok(py.eval('a + day == date(2002, 3, 3)', ctx));
        ok(py.eval('day + a == date(2002, 3, 3)', ctx)); // 5
        ok(py.eval('a - day == date(2002, 3, 1)', ctx));
        ok(py.eval('-day + a == date(2002, 3, 1)', ctx));
        ok(py.eval('a + week == date(2002, 3, 9)', ctx));
        ok(py.eval('a - week == date(2002, 2, 23)', ctx));
        ok(py.eval('a + 52*week == date(2003, 3, 1)', ctx)); // 10
        ok(py.eval('a - 52*week == date(2001, 3, 3)', ctx));
        ok(py.eval('(a + week) - a == week', ctx));
        ok(py.eval('(a + day) - a == day', ctx));
        ok(py.eval('(a - week) - a == -week', ctx));
        ok(py.eval('(a - day) - a == -day', ctx)); // 15
        ok(py.eval('a - (a + week) == -week', ctx));
        ok(py.eval('a - (a + day) == -day', ctx));
        ok(py.eval('a - (a - week) == week', ctx));
        ok(py.eval('a - (a - day) == day', ctx));

        raises(function () {
            py.eval('a + 1', ctx);
        }, /^Error: TypeError:/); // 20
        raises(function () {
            py.eval('a - 1', ctx);
        }, /^Error: TypeError:/);
        raises(function () {
            py.eval('1 + a', ctx);
        }, /^Error: TypeError:/);
        raises(function () {
            py.eval('1 - a', ctx);
        }, /^Error: TypeError:/);

        // delta - date is senseless.
        raises(function () {
            py.eval('day - a', ctx);
        }, /^Error: TypeError:/);
        // mixing date and (delta or date) via * or // is senseless
        raises(function () {
            py.eval('day * a', ctx);
        }, /^Error: TypeError:/); // 25
        raises(function () {
            py.eval('a * day', ctx);
        }, /^Error: TypeError:/);
        raises(function () {
            py.eval('day // a', ctx);
        }, /^Error: TypeError:/);
        raises(function () {
            py.eval('a // day', ctx);
        }, /^Error: TypeError:/);
        raises(function () {
            py.eval('a * a', ctx);
        }, /^Error: TypeError:/);
        raises(function () {
            py.eval('a // a', ctx);
        }, /^Error: TypeError:/); // 30
        // date + date is senseless
        raises(function () {
            py.eval('a + a', ctx);
        }, /^Error: TypeError:/);
    });
});
openerp.testing.section('eval.edc', {
    dependencies: ['web.data'],
    rpc: 'rpc',
    setup: function (instance) {
        instance.edc = function (domains, contexts) {
            return this.session.rpc('/web/session/eval_domain_and_context', {
                contexts: contexts || [],
                domains: domains || []
            });
        }
    }
}, function (test) {
    test('empty, basic', {asserts: 3}, function (instance) {
        return instance.edc().then(function (result) {
            // default values for new db
            deepEqual(result.context, {
                lang: 'en_US',
                tz: false,
                uid: 1
            });
            deepEqual(result.domain, []);
            deepEqual(result.group_by, []);
        });
    });
    test('empty, context altered', {
        asserts: 3,
        setup: function (instance) {
            var lang = new instance.web.Model('res.lang');
            var users = new instance.web.Model('res.users');
            return lang.call('load_lang', ['ru_RU']).then(function () {
                return users.call('write', [instance.session.uid, {
                    lang: 'ru_RU',
                    tz: 'America/Santarem'
                }]);
            }).then(function () {
                return instance.session.session_reload();
            });
        }
    }, function (instance) {
        return instance.edc().then(function (result) {
            // default values for new db
            deepEqual(result.context, {
                lang: 'ru_RU',
                tz: 'America/Santarem',
                uid: 1
            });
            deepEqual(result.domain, []);
            deepEqual(result.group_by, []);
        });
    });
    test('context_merge_00', {asserts: 1}, function (instance) {
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
        return instance.edc([], ctx).then(function (result) {
            deepEqual(result.context, {
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
    });
    test('context_merge_01', {asserts: 1}, function (instance) {
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
        return instance.edc([], ctx).then(function (result) {
            deepEqual(result.context, {
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
    });
});
openerp.testing.section('eval.edc.nonliterals', {
    dependencies: ['web.data'],
    rpc: 'rpc',
    setup: function (instance) {
        _.extend(instance, {
            edc: function (domains, contexts) {
                return this.session.rpc('/web/session/eval_domain_and_context', {
                    contexts: contexts || [],
                    domains: domains || []
                });
            },
            load_context: function (index) {
                return this.session.rpc('/web/tests/load_context', {index: index});
            },
            load_domain: function (index) {
                return this.session.rpc('/web/tests/load_domain', {index: index});
            },
        });
    }
}, function (test) {
    test('domain with time', {asserts: 2}, function (instance) {
        return instance.load_domain(0).then(function (d) {
            strictEqual(d.__ref, 'domain');
            return instance.edc([
                [['type', '=', 'contract']],
                { "__domains": [["|"], [["state", "in", ["open", "draft"]]], [["state", "=", "pending"]]],
                  "__eval_context": null,
                  "__ref": "compound_domain"
                },
                d,
                [['user_id', '=', 1]]
            ])
        }).then(function (result) {
            var d = new Date();
            var today = _.str.sprintf("%04d-%02d-%02d",
                d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate());
            deepEqual(result.domain, [
                ["type", "=", "contract"],
                "|", ["state", "in", ["open", "draft"]],
                     ["state", "=", "pending"],
                "|",
                    "&", ["date", "!=", false],
                         ["date", "<=", today],
                    ["is_overdue_quantity", "=", true],
                ["user_id", "=", 1]
            ]);
        });
    });
    test('conditional context', {asserts: 2}, function (instance) {
        return instance.load_domain(1).then(function (d) {
            var e1 = instance.edc([d]).then(function (result) {
                deepEqual(result.domain, [
                    ['company_id', '=', false]
                ]);
            });
            var cd = new instance.web.CompoundDomain(d);
            cd.set_eval_context({company_id: 42});
            var e2 = instance.edc([cd]).then(function (result) {
                deepEqual(result.domain, [
                    ['company_id', '=', 42]
                ]);
            });

            return $.when(e1, e2);
        });
    });
    test('substitution in context', {asserts: 1}, function (instance) {
        return instance.load_context(0).then(function (c) {
            var cc = new instance.web.CompoundContext(c);
            cc.set_eval_context({active_id: 42});
            return instance.edc([], [cc]);
        }).then(function (result) {
            deepEqual(result.context, {
                lang: "en_US",
                tz: false,
                uid: 1,
                default_opportunity_id: 42,
                default_duration: 1.0,
                lng: "en_US"
            });
        });
    });
    test('date', {asserts: 1}, function (instance) {
        return instance.load_domain(4).then(function (d) {
            return instance.edc([d]);
        }).then(function (result) {
            var d = new Date();
            var today = _.str.sprintf("%04d-%02d-%02d",
                d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate());
            deepEqual(result.domain, [
                ['state', '!=', 'cancel'],
                ['opening_date', '>', today]
            ]);
        });
    });
    test('delta', {asserts: 1}, function (instance) {
        return instance.load_domain(5).then(function (d) {
            return instance.edc([d]);
        }).then(function (result) {
            var d = new Date();
            var today = _.str.sprintf("%04d-%02d-%02d",
                d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate());
            d.setDate(d.getDate() - 15);
            var ago_15_d = _.str.sprintf("%04d-%02d-%02d",
                d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate());
            deepEqual(result.domain, [
                ['type', '=', 'in'],
                ['day', '<=', today],
                ['day', '>', ago_15_d]
            ]);
        });
    });
});
openerp.testing.section('eval.contexts', {
    dependencies: ['web.coresetup']
}, function (test) {
    test('context_recursive', function (instance) {
        var context_to_eval = [{
            __ref: 'context',
            __debug: '{"foo": context.get("bar", "qux")}'
        }];
        deepEqual(
            instance.web.pyeval.eval('contexts', context_to_eval, {bar: "ok"}),
            {foo: 'ok'});
        deepEqual(
            instance.web.pyeval.eval('contexts', context_to_eval, {bar: false}),
            {foo: false});
        deepEqual(
            instance.web.pyeval.eval('contexts', context_to_eval),
            {foo: 'qux'});
    });
    test('context_sequences', function (instance) {
        // Context n should have base evaluation context + all of contexts
        // 0..n-1 in its own evaluation context
        var active_id = 4;
        var result = instance.web.pyeval.eval('contexts', [
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

        deepEqual(result, {
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
    test('non-literal_eval_contexts', function (instance) {
        var result = instance.web.pyeval.eval('contexts', [{
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
                                 "fiscal_position": false,
                                 "date_invoice": false, "period_id": false,
                                 "payment_term": false, "reference_type": "none",
                                 "reference": false, "account_id": 440,
                                 "name": false, "invoice_line": [],
                                 "tax_line": [], "amount_untaxed": 0,
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
                    "uos_id": 1,
                    "price_unit": 100,
                    "account_id": 853,
                    "discount": 0,
                    "account_analytic_id": false,
                    "company_id": false,
                    "note": false,
                    "invoice_line_tax_id": [[6, false, [1]]],
                    "active_id": false,
                    "active_ids": [],
                    "active_model": "account.invoice.line",
                    "parent": {
                        "id": false, "journal_id": 10, "number": false,
                        "type": "out_invoice", "currency_id": 1,
                        "partner_id": 4, "fiscal_position": false,
                        "date_invoice": false, "period_id": false,
                        "payment_term": false, "reference_type": "none",
                        "reference": false, "account_id": 440, "name": false,
                        "tax_line": [], "amount_untaxed": 0, "amount_tax": 0,
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
        deepEqual(result, {type: 'out_invoice'});
    });
});
openerp.testing.section('eval.domains', {
    dependencies: ['web.coresetup', 'web.dates']
}, function (test) {
    test('current_date', function (instance) {
        var current_date = instance.web.date_to_str(new Date());
        var result = instance.web.pyeval.eval('domains',
            [[],{"__ref":"domain","__debug":"[('name','>=',current_date),('name','<=',current_date)]","__id":"5dedcfc96648"}],
            instance.web.pyeval.context());
        deepEqual(result, [
            ['name', '>=', current_date],
            ['name', '<=', current_date]
        ]);
    });
    test('context_freevar', function (instance) {
        var domains_to_eval = [{
            __ref: 'domain',
            __debug: '[("foo", "=", context.get("bar", "qux"))]'
        }, [['bar', '>=', 42]]];
        deepEqual(
            instance.web.pyeval.eval('domains', domains_to_eval, {bar: "ok"}),
            [['foo', '=', 'ok'], ['bar', '>=', 42]]);
        deepEqual(
            instance.web.pyeval.eval('domains', domains_to_eval, {bar: false}),
            [['foo', '=', false], ['bar', '>=', 42]]);
        deepEqual(
            instance.web.pyeval.eval('domains', domains_to_eval),
            [['foo', '=', 'qux'], ['bar', '>=', 42]]);
    });
});
openerp.testing.section('eval.groupbys', {
    dependencies: ['web.coresetup']
}, function (test) {
    test('groupbys_00', function (instance) {
        var result = instance.web.pyeval.eval('groupbys', [
            {group_by: 'foo'},
            {group_by: ['bar', 'qux']},
            {group_by: null},
            {group_by: 'grault'}
        ]);
        deepEqual(result, ['foo', 'bar', 'qux', 'grault']);
    });
    test('groupbys_01', function (instance) {
        var result = instance.web.pyeval.eval('groupbys', [
            {group_by: 'foo'},
            { __ref: 'context', __debug: '{"group_by": "bar"}' },
            {group_by: 'grault'}
        ]);
        deepEqual(result, ['foo', 'bar', 'grault']);
    });
    test('groupbys_02', function (instance) {
        var result = instance.web.pyeval.eval('groupbys', [
            {group_by: 'foo'},
            {
                __ref: 'compound_context',
                __contexts: [ {group_by: 'bar'} ],
                __eval_context: null
            },
            {group_by: 'grault'}
        ]);
        deepEqual(result, ['foo', 'bar', 'grault']);
    });
    test('groupbys_03', function (instance) {
        var result = instance.web.pyeval.eval('groupbys', [
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
        deepEqual(result, ['foo', 'bar', 'grault']);
    });
    test('groupbys_04', function (instance) {
        var result = instance.web.pyeval.eval('groupbys', [
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
        deepEqual(result, ['foo', 'bar', 'grault']);
    });
    test('groupbys_05', function (instance) {
        var result = instance.web.pyeval.eval('groupbys', [
            {group_by: 'foo'},
            { __ref: 'context', __debug: '{"group_by": value}' },
            {group_by: 'grault'}
        ], { value: 'bar' });
        deepEqual(result, ['foo', 'bar', 'grault']);
    });
});
