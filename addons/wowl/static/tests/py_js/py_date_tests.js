/** @odoo-module **/
import { evaluateExpr } from "../../src/py_js/py";

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
      assert.ok(check("time.strftime('%Y') + '-01-30'", (d) => String(d.getFullYear()) + "-01-30"));
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

    QUnit.test("datetime.datetime.combine", (assert) => {
      const expr =
        "datetime.datetime.combine(context_today(), datetime.time(23,59,59)).strftime('%Y-%m-%d %H:%M:%S')";
      assert.ok(
        check(expr, (d) => {
          return formatDate(d) + " 23:59:59";
        })
      );
    });

    // datetime.datetime.combine(context_today(), datetime.time(23,59,59))
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

    QUnit.module("relativedelta");

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

    QUnit.module("datetime.timedelta");

    QUnit.test("adding date and time delta", (assert) => {
      const expr =
        "(datetime.date(day=3,month=4,year=2001) + datetime.timedelta(days=-1)).strftime('%Y-%m-%d')";
      assert.strictEqual(evaluateExpr(expr), "2001-04-02");
    });

    QUnit.test("adding time delta and date", (assert) => {
      const expr =
        "(datetime.timedelta(days=-1) + datetime.date(day=3,month=4,year=2001)).strftime('%Y-%m-%d')";
      assert.strictEqual(evaluateExpr(expr), "2001-04-02");
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
  });
});
