/** @odoo-module **/

import { evaluateExpr } from "@web/core/py_js/py";
import { patchDate, patchWithCleanup } from "@web/../tests/helpers/utils";
import { PyDate, PyTimeDelta } from "@web/core/py_js/py_date";

QUnit.module("py", {}, () => {
    QUnit.module("date stuff", () => {
        QUnit.module("time");

        function check(expr, fn) {
            const d0 = new Date();
            const result = evaluateExpr(expr);
            const d1 = new Date();
            return fn(d0) <= result && result <= fn(d1);
        }
        const format = (n) => String(n).padStart(2, "0");
        const formatDate = (d) => {
            const year = d.getUTCFullYear();
            const month = format(d.getUTCMonth() + 1);
            const day = format(d.getUTCDate());
            return `${year}-${month}-${day}`;
        };
        const formatDateTime = (d) => {
            const h = format(d.getUTCHours());
            const m = format(d.getUTCMinutes());
            const s = format(d.getUTCSeconds());
            return `${formatDate(d)} ${h}:${m}:${s}`;
        };

        QUnit.test("strftime", (assert) => {
            assert.ok(check("time.strftime('%Y')", (d) => String(d.getFullYear())));
            assert.ok(
                check("time.strftime('%Y') + '-01-30'", (d) => String(d.getFullYear()) + "-01-30")
            );
            assert.ok(check("time.strftime('%Y-%m-%d %H:%M:%S')", formatDateTime));
        });

        QUnit.module("datetime.datetime");

        QUnit.test("datetime.datetime.now", (assert) => {
            assert.ok(check("datetime.datetime.now().year", (d) => d.getUTCFullYear()));
            assert.ok(check("datetime.datetime.now().month", (d) => d.getUTCMonth() + 1));
            assert.ok(check("datetime.datetime.now().day", (d) => d.getUTCDate()));
            assert.ok(check("datetime.datetime.now().hour", (d) => d.getUTCHours()));
            assert.ok(check("datetime.datetime.now().minute", (d) => d.getUTCMinutes()));
            assert.ok(check("datetime.datetime.now().second", (d) => d.getUTCSeconds()));
        });

        QUnit.test("various operations", (assert) => {
            const expr1 = "datetime.datetime(day=3,month=4,year=2001).strftime('%Y-%m-%d')";
            assert.strictEqual(evaluateExpr(expr1), "2001-04-03");
            const expr2 = "datetime.datetime(2001, 4, 3).strftime('%Y-%m-%d')";
            assert.strictEqual(evaluateExpr(expr2), "2001-04-03");
            const expr3 =
                "datetime.datetime(day=3,month=4,second=12, year=2001,minute=32).strftime('%Y-%m-%d %H:%M:%S')";
            assert.strictEqual(evaluateExpr(expr3), "2001-04-03 00:32:12");
        });

        QUnit.test("to_utc", (assert) => {
            patchDate(2021, 8, 17, 10, 0, 0);
            patchWithCleanup(Date.prototype, {
                getTimezoneOffset() {
                    return -360;
                },
            });

            const expr =
                "datetime.datetime.combine(context_today(), datetime.time(0,0,0)).to_utc()";

            assert.strictEqual(JSON.stringify(evaluateExpr(expr)), `"2021-09-16 18:00:00"`);
        });

        QUnit.test("to_utc in october with winter/summer change", (assert) => {
            patchDate(2021, 9, 17, 10, 0, 0);
            patchWithCleanup(Date.prototype, {
                getTimezoneOffset() {
                    const month = this.getMonth() // starts at 0;
                    if (10 <= month || month <= 2) {
                        //rough approximation
                        return -60;
                    } else {
                        return -120;
                    }
                },
            });
            const expr =
                "datetime.datetime(2022, 10, 17).to_utc()";
            assert.strictEqual(JSON.stringify(evaluateExpr(expr)), `"2022-10-16 22:00:00"`);
        });

        QUnit.test("datetime.datetime.combine", (assert) => {
            const expr =
                "datetime.datetime.combine(context_today(), datetime.time(23,59,59)).strftime('%Y-%m-%d %H:%M:%S')";
            assert.ok(
                check(expr, (d) => {
                    return formatDate(d) + " 23:59:59";
                })
            );
        });

        QUnit.test("datetime.datetime.toJSON", (assert) => {
            assert.strictEqual(
                JSON.stringify(evaluateExpr("datetime.datetime(day=3,month=4,year=2001,hour=10)")),
                `"2001-04-03 10:00:00"`
            );
        });

        QUnit.test("datetime + timedelta", function (assert) {
            assert.expect(6);

            assert.strictEqual(
                evaluateExpr(
                    "(datetime.datetime(2017, 2, 15, 1, 7, 31) + datetime.timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')"
                ),
                "2017-02-16 01:07:31"
            );
            assert.strictEqual(
                evaluateExpr(
                    "(datetime.datetime(2012, 2, 15, 1, 7, 31) - datetime.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')"
                ),
                "2012-02-15 00:07:31"
            );
            assert.strictEqual(
                evaluateExpr(
                    "(datetime.datetime(2012, 2, 15, 1, 7, 31) + datetime.timedelta(hours=-1)).strftime('%Y-%m-%d %H:%M:%S')"
                ),
                "2012-02-15 00:07:31"
            );
            assert.strictEqual(
                evaluateExpr(
                    "(datetime.datetime(2012, 2, 15, 1, 7, 31) + datetime.timedelta(minutes=100)).strftime('%Y-%m-%d %H:%M:%S')"
                ),
                "2012-02-15 02:47:31"
            );
            assert.strictEqual(
                evaluateExpr(
                    "(datetime.date(day=3,month=4,year=2001) + datetime.timedelta(days=-1)).strftime('%Y-%m-%d')"
                ),
                "2001-04-02"
            );
            assert.strictEqual(
                evaluateExpr(
                    "(datetime.timedelta(days=-1) + datetime.date(day=3,month=4,year=2001)).strftime('%Y-%m-%d')"
                ),
                "2001-04-02"
            );
        });

        QUnit.module("datetime.date");

        QUnit.test("datetime.date.today", (assert) => {
            assert.ok(check("(datetime.date.today()).strftime('%Y-%m-%d')", formatDate));
        });

        QUnit.test("various operations", (assert) => {
            const expr1 = "datetime.date(day=3,month=4,year=2001).strftime('%Y-%m-%d')";
            assert.strictEqual(evaluateExpr(expr1), "2001-04-03");
            const expr2 = "datetime.date(2001, 4, 3).strftime('%Y-%m-%d')";
            assert.strictEqual(evaluateExpr(expr2), "2001-04-03");
        });

        QUnit.test("datetime.date.toJSON", (assert) => {
            assert.strictEqual(
                JSON.stringify(evaluateExpr("datetime.date(year=1997,month=5,day=18)")),
                `"1997-05-18"`
            );
        });

        QUnit.test("basic operations with dates", function (assert) {
            assert.expect(19);

            let ctx = {
                d1: PyDate.create(2002, 1, 31),
                d2: PyDate.create(1956, 1, 31),
            };

            assert.strictEqual(evaluateExpr("(d1 - d2).days", ctx), 46 * 365 + 12);
            assert.strictEqual(evaluateExpr("(d1 - d2).seconds", ctx), 0);
            assert.strictEqual(evaluateExpr("(d1 - d2).microseconds", ctx), 0);

            ctx = {
                a: PyDate.create(2002, 3, 2),
                day: PyTimeDelta.create({ days: 1 }),
                week: PyTimeDelta.create({ days: 7 }),
                date: PyDate,
            };

            assert.ok(evaluateExpr("a + day == date(2002, 3, 3)", ctx));
            assert.ok(evaluateExpr("day + a == date(2002, 3, 3)", ctx)); // 5
            assert.ok(evaluateExpr("a - day == date(2002, 3, 1)", ctx));
            assert.ok(evaluateExpr("-day + a == date(2002, 3, 1)", ctx));
            assert.ok(evaluateExpr("a + week == date(2002, 3, 9)", ctx));
            assert.ok(evaluateExpr("a - week == date(2002, 2, 23)", ctx));
            assert.ok(evaluateExpr("a + 52*week == date(2003, 3, 1)", ctx)); // 10
            assert.ok(evaluateExpr("a - 52*week == date(2001, 3, 3)", ctx));
            assert.ok(evaluateExpr("(a + week) - a == week", ctx));
            assert.ok(evaluateExpr("(a + day) - a == day", ctx));
            assert.ok(evaluateExpr("(a - week) - a == -week", ctx));
            assert.ok(evaluateExpr("(a - day) - a == -day", ctx)); // 15
            assert.ok(evaluateExpr("a - (a + week) == -week", ctx));
            assert.ok(evaluateExpr("a - (a + day) == -day", ctx));
            assert.ok(evaluateExpr("a - (a - week) == week", ctx));
            assert.ok(evaluateExpr("a - (a - day) == day", ctx));

            // assert.throws(function () {
            //     evaluateExpr("a + 1", ctx);
            // }, /^Error: TypeError:/); //20
            // assert.throws(function () {
            //     evaluateExpr("a - 1", ctx);
            // }, /^Error: TypeError:/);
            // assert.throws(function () {
            //     evaluateExpr("1 + a", ctx);
            // }, /^Error: TypeError:/);
            // assert.throws(function () {
            //     evaluateExpr("1 - a", ctx);
            // }, /^Error: TypeError:/);

            // // delta - date is senseless.
            // assert.throws(function () {
            //     evaluateExpr("day - a", ctx);
            // }, /^Error: TypeError:/);
            // // mixing date and (delta or date) via * or // is senseless
            // assert.throws(function () {
            //     evaluateExpr("day * a", ctx);
            // }, /^Error: TypeError:/); // 25
            // assert.throws(function () {
            //     evaluateExpr("a * day", ctx);
            // }, /^Error: TypeError:/);
            // assert.throws(function () {
            //     evaluateExpr("day // a", ctx);
            // }, /^Error: TypeError:/);
            // assert.throws(function () {
            //     evaluateExpr("a // day", ctx);
            // }, /^Error: TypeError:/);
            // assert.throws(function () {
            //     evaluateExpr("a * a", ctx);
            // }, /^Error: TypeError:/);
            // assert.throws(function () {
            //     evaluateExpr("a // a", ctx);
            // }, /^Error: TypeError:/); // 30
            // // date + date is senseless
            // assert.throws(function () {
            //     evaluateExpr("a + a", ctx);
            // }, /^Error: TypeError:/);
        });

        QUnit.module("datetime.time");

        QUnit.test("various operations", (assert) => {
            const expr1 = "datetime.time(hour=3,minute=2. second=1).strftime('%H:%M:%S')";
            assert.strictEqual(evaluateExpr(expr1), "03:02:01");
        });

        QUnit.test("attributes", (assert) => {
            const expr1 = "datetime.time(hour=3,minute=2. second=1).hour";
            assert.strictEqual(evaluateExpr(expr1), 3);
            const expr2 = "datetime.time(hour=3,minute=2. second=1).minute";
            assert.strictEqual(evaluateExpr(expr2), 2);
            const expr3 = "datetime.time(hour=3,minute=2. second=1).second";
            assert.strictEqual(evaluateExpr(expr3), 1);
        });

        QUnit.test("datetime.time.toJSON", (assert) => {
            assert.strictEqual(
                JSON.stringify(evaluateExpr("datetime.time(hour=11,minute=45,second=15)")),
                `"11:45:15"`
            );
        });

        QUnit.module("relativedelta relative : period is plural", () => {
            QUnit.test("adding date and relative delta", (assert) => {
                const expr1 =
                    "(datetime.date(day=3,month=4,year=2001) + relativedelta(days=-1)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr1), "2001-04-02");
                const expr2 =
                    "(datetime.date(day=3,month=4,year=2001) + relativedelta(weeks=-1)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr2), "2001-03-27");
            });

            QUnit.test("adding relative delta and date", (assert) => {
                const expr =
                    "(relativedelta(days=-1) + datetime.date(day=3,month=4,year=2001)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr), "2001-04-02");
            });

            QUnit.test(
                "adding/substracting relative delta and date -- shifts order of magnitude",
                (assert) => {
                    const expr =
                        "(relativedelta(hours=14) + datetime.datetime(hour=15,day=3,month=4,year=2001)).strftime('%Y-%m-%d %H:%M:%S')";
                    assert.strictEqual(evaluateExpr(expr), "2001-04-04 05:00:00");

                    const expr2 =
                        "(relativedelta(days=32) + datetime.date(day=3,month=4,year=2001)).strftime('%Y-%m-%d')";
                    assert.strictEqual(evaluateExpr(expr2), "2001-05-05");

                    const expr3 =
                        "(relativedelta(months=14) + datetime.date(day=3,month=4,year=2001)).strftime('%Y-%m-%d')";
                    assert.strictEqual(evaluateExpr(expr3), "2002-06-03");

                    const expr4 =
                        "(datetime.datetime(hour=13,day=3,month=4,year=2001) - relativedelta(hours=14)).strftime('%Y-%m-%d %H:%M:%S')";
                    assert.strictEqual(evaluateExpr(expr4), "2001-04-02 23:00:00");

                    const expr5 =
                        "(datetime.date(day=3,month=4,year=2001) - relativedelta(days=4)).strftime('%Y-%m-%d')";
                    assert.strictEqual(evaluateExpr(expr5), "2001-03-30");

                    const expr6 =
                        "(datetime.date(day=3,month=4,year=2001) - relativedelta(months=5)).strftime('%Y-%m-%d')";
                    assert.strictEqual(evaluateExpr(expr6), "2000-11-03");
                }
            );

            QUnit.test("substracting date and relative delta", (assert) => {
                const expr1 =
                    "(datetime.date(day=3,month=4,year=2001) - relativedelta(days=-1)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr1), "2001-04-04");
                const expr2 =
                    "(datetime.date(day=3,month=4,year=2001) - relativedelta(weeks=-1)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr2), "2001-04-10");
                const expr3 =
                    "(datetime.date(day=3,month=4,year=2001) - relativedelta(days=1)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr3), "2001-04-02");
                const expr4 =
                    "(datetime.date(day=3,month=4,year=2001) - relativedelta(weeks=1)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr4), "2001-03-27");
            });
        });

        QUnit.module("relativedelta absolute : period is singular", () => {
            QUnit.test("throws when period negative", (assert) => {
                const matcher = (errorMessage) => {
                    return function match(err) {
                        return err.message === errorMessage;
                    };
                };

                const expr1 = "relativedelta(day=-1)";
                assert.throws(() => evaluateExpr(expr1), matcher("day -1 is out of range"));

                const expr2 = "relativedelta(month=-1)";
                assert.throws(() => evaluateExpr(expr2), matcher("month -1 is out of range"));
            });

            QUnit.test("adding date and relative delta", (assert) => {
                const expr1 =
                    "(datetime.date(day=3,month=4,year=2001) + relativedelta(day=1)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr1), "2001-04-01");

                const expr2 =
                    "(datetime.date(day=3,month=4,year=2001) + relativedelta(month=1)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr2), "2001-01-03");

                const expr3 =
                    "(datetime.date(2021,10,1) + relativedelta(hours=12)).strftime('%Y-%m-%d %H:%M:%S')";
                assert.strictEqual(evaluateExpr(expr3), "2021-10-01 12:00:00");

                const expr4 =
                    "(datetime.date(2021,10,1) + relativedelta(day=15,days=3)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr4), "2021-10-18");

                const expr5 =
                    "(datetime.date(2021,10,1) - relativedelta(day=15,days=3)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr5), "2021-10-12");

                const expr6 =
                    "(datetime.date(2021,10,1) + relativedelta(day=15,days=3,hours=24)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr6), "2021-10-19");
            });

            QUnit.test("adding relative delta and date", (assert) => {
                const expr =
                    "(relativedelta(day=1) + datetime.date(day=3,month=4,year=2001)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr), "2001-04-01");
            });

            QUnit.test("substracting date and relative delta", (assert) => {
                const expr1 =
                    "(datetime.date(day=3,month=4,year=2001) - relativedelta(day=1)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr1), "2001-04-01");

                const expr3 =
                    "(datetime.date(day=3,month=4,year=2001) - relativedelta(day=1)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr3), "2001-04-01");
            });

            QUnit.test("type of date + relative delta", (assert) => {
                const expr1 = "(datetime.date(2021,10,1) + relativedelta(day=15,days=3,hours=24))";
                assert.ok(evaluateExpr(expr1) instanceof PyDate);
            });
        });

        QUnit.module("relative delta weekday", () => {
            QUnit.test("add or substract weekday", (assert) => {
                const expr1 =
                    "(datetime.date(day=3,month=4,year=2001) - relativedelta(day=1, weekday=3)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr1), "2001-04-05");

                const expr2 =
                    "(datetime.date(day=29,month=4,year=2001) - relativedelta(weekday=4)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr2), "2001-05-04");

                const expr3 =
                    "(datetime.date(day=6,month=4,year=2001) - relativedelta(weekday=0)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr3), "2001-04-09");

                const expr4 =
                    "(datetime.date(day=1,month=4,year=2001) + relativedelta(weekday=-2)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr4), "2001-04-07");

                const expr5 =
                    "(datetime.date(day=11,month=4,year=2001) + relativedelta(weekday=2)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr5), "2001-04-11");

                const expr6 =
                    "(datetime.date(day=11,month=4,year=2001) + relativedelta(weekday=-2)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr6), "2001-04-14");

                const expr7 =
                    "(datetime.date(day=11,month=4,year=2001) + relativedelta(weekday=0)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr7), "2001-04-16");

                const expr8 =
                    "(datetime.date(day=11,month=4,year=2001) + relativedelta(weekday=1)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr8), "2001-04-17");
            });
        });

        QUnit.module("relative delta yearday nlyearday", () => {
            QUnit.test("yearday", (assert) => {
                const expr1 =
                    "(datetime.date(day=3,month=4,year=2001) - relativedelta(year=2000, yearday=60)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr1), "2000-02-29");

                const expr2 =
                    "(datetime.date(day=3,month=4,year=2001) - relativedelta(yearday=60)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr2), "2001-03-01");

                const expr3 =
                    "(datetime.date(1999,12,31) + relativedelta(days=1, yearday=60)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr3), "1999-03-02");
            });

            QUnit.test("nlyearday", (assert) => {
                const expr1 =
                    "(datetime.date(day=3,month=4,year=2001) + relativedelta(year=2000, nlyearday=60)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr1), "2000-03-01");

                const expr2 =
                    "(datetime.date(day=3,month=4,year=2001) + relativedelta(nlyearday=60)).strftime('%Y-%m-%d')";
                assert.strictEqual(evaluateExpr(expr2), "2001-03-01");
            });
        });

        QUnit.module("misc");

        QUnit.test("context_today", (assert) => {
            assert.ok(check("context_today().strftime('%Y-%m-%d')", formatDate));
        });

        QUnit.test("today", (assert) => {
            assert.ok(check("today", formatDate));
        });

        QUnit.test("now", (assert) => {
            assert.ok(check("now", formatDateTime));
        });

        QUnit.test("current_date", (assert) => {
            patchDate(2021, 8, 20, 10, 0, 0);
            assert.deepEqual(evaluateExpr("current_date"), "2021-09-20");
        });
    });
});
