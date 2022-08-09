/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { PyDate } from "../../src/core/py_js/py_date";
import { patchWithCleanup } from "../helpers/utils";

QUnit.module("domain", {}, () => {
    // ---------------------------------------------------------------------------
    // Basic properties
    // ---------------------------------------------------------------------------
    QUnit.module("Basic Properties");

    QUnit.test("empty", function (assert) {
        assert.ok(new Domain([]).contains({}));
        assert.strictEqual(new Domain([]).toString(), "[]");
        assert.deepEqual(new Domain([]).toList(), []);
    });

    QUnit.test("undefined domain", function (assert) {
        assert.ok(new Domain(undefined).contains({}));
        assert.strictEqual(new Domain(undefined).toString(), "[]");
        assert.deepEqual(new Domain(undefined).toList(), []);
    });

    QUnit.test("simple condition", function (assert) {
        assert.ok(new Domain([["a", "=", 3]]).contains({ a: 3 }));
        assert.notOk(new Domain([["a", "=", 3]]).contains({ a: 5 }));
        assert.strictEqual(new Domain([["a", "=", 3]]).toString(), `[("a", "=", 3)]`);
        assert.deepEqual(new Domain([["a", "=", 3]]).toList(), [["a", "=", 3]]);
    });

    QUnit.test("can be created from domain", function (assert) {
        const domain = new Domain([["a", "=", 3]]);
        assert.strictEqual(new Domain(domain).toString(), `[("a", "=", 3)]`);
    });

    QUnit.test("basic", function (assert) {
        const record = {
            a: 3,
            group_method: "line",
            select1: "day",
            rrule_type: "monthly",
        };
        assert.ok(new Domain([["a", "=", 3]]).contains(record));
        assert.notOk(new Domain([["a", "=", 5]]).contains(record));
        assert.ok(new Domain([["group_method", "!=", "count"]]).contains(record));
        assert.ok(
            new Domain([
                ["select1", "=", "day"],
                ["rrule_type", "=", "monthly"],
            ]).contains(record)
        );
    });

    QUnit.test("or", function (assert) {
        const currentDomain = [
            "|",
            ["section_id", "=", 42],
            "|",
            ["user_id", "=", 3],
            ["member_ids", "in", [3]],
        ];
        const record = {
            section_id: null,
            user_id: null,
            member_ids: null,
        };
        assert.ok(new Domain(currentDomain).contains({ ...record, section_id: 42 }));
        assert.ok(new Domain(currentDomain).contains({ ...record, user_id: 3 }));
        assert.ok(new Domain(currentDomain).contains({ ...record, member_ids: 3 }));
    });

    QUnit.test("and", function (assert) {
        const domain = new Domain(["&", "&", ["a", "=", 1], ["b", "=", 2], ["c", "=", 3]]);

        assert.ok(domain.contains({ a: 1, b: 2, c: 3 }));
        assert.notOk(domain.contains({ a: -1, b: 2, c: 3 }));
        assert.notOk(domain.contains({ a: 1, b: -1, c: 3 }));
        assert.notOk(domain.contains({ a: 1, b: 2, c: -1 }));
    });

    QUnit.test("not", function (assert) {
        const record = {
            a: 5,
            group_method: "line",
        };
        assert.ok(new Domain(["!", ["a", "=", 3]]).contains(record));
        assert.ok(new Domain(["!", ["group_method", "=", "count"]]).contains(record));
    });

    QUnit.test("like, =like, ilike and =ilike", function (assert) {
        assert.expect(16);

        assert.ok(new Domain([["a", "like", "value"]]).contains({ a: "value" }));
        assert.ok(new Domain([["a", "like", "value"]]).contains({ a: "some value" }));
        assert.notOk(new Domain([["a", "like", "value"]]).contains({ a: "Some Value" }));
        assert.notOk(new Domain([["a", "like", "value"]]).contains({ a: false }));

        assert.ok(new Domain([["a", "=like", "%value"]]).contains({ a: "value" }));
        assert.ok(new Domain([["a", "=like", "%value"]]).contains({ a: "some value" }));
        assert.notOk(new Domain([["a", "=like", "%value"]]).contains({ a: "Some Value" }));
        assert.notOk(new Domain([["a", "=like", "%value"]]).contains({ a: false }));

        assert.ok(new Domain([["a", "ilike", "value"]]).contains({ a: "value" }));
        assert.ok(new Domain([["a", "ilike", "value"]]).contains({ a: "some value" }));
        assert.ok(new Domain([["a", "ilike", "value"]]).contains({ a: "Some Value" }));
        assert.notOk(new Domain([["a", "ilike", "value"]]).contains({ a: false }));

        assert.ok(new Domain([["a", "=ilike", "%value"]]).contains({ a: "value" }));
        assert.ok(new Domain([["a", "=ilike", "%value"]]).contains({ a: "some value" }));
        assert.ok(new Domain([["a", "=ilike", "%value"]]).contains({ a: "Some Value" }));
        assert.notOk(new Domain([["a", "=ilike", "%value"]]).contains({ a: false }));
    });

    QUnit.test("complex domain", function (assert) {
        const domain = new Domain(["&", "!", ["a", "=", 1], "|", ["a", "=", 2], ["a", "=", 3]]);

        assert.notOk(domain.contains({ a: 1 }));
        assert.ok(domain.contains({ a: 2 }));
        assert.ok(domain.contains({ a: 3 }));
        assert.notOk(domain.contains({ a: 4 }));
    });

    QUnit.test("toList", function (assert) {
        assert.deepEqual(new Domain([]).toList(), []);
        assert.deepEqual(new Domain([["a", "=", 3]]).toList(), [["a", "=", 3]]);
        assert.deepEqual(
            new Domain([
                ["a", "=", 3],
                ["b", "!=", "4"],
            ]).toList(),
            ["&", ["a", "=", 3], ["b", "!=", "4"]]
        );
        assert.deepEqual(new Domain(["!", ["a", "=", 3]]).toList(), ["!", ["a", "=", 3]]);
    });

    QUnit.test("toString", function (assert) {
        assert.strictEqual(new Domain([]).toString(), `[]`);
        assert.strictEqual(new Domain([["a", "=", 3]]).toString(), `[("a", "=", 3)]`);
        assert.strictEqual(
            new Domain([
                ["a", "=", 3],
                ["b", "!=", "4"],
            ]).toString(),
            `["&", ("a", "=", 3), ("b", "!=", "4")]`
        );
        assert.strictEqual(new Domain(["!", ["a", "=", 3]]).toString(), `["!", ("a", "=", 3)]`);
        assert.strictEqual(new Domain([["name", "=", null]]).toString(), '[("name", "=", None)]');
        assert.strictEqual(new Domain([["name", "=", false]]).toString(), '[("name", "=", False)]');
        assert.strictEqual(new Domain([["name", "=", true]]).toString(), '[("name", "=", True)]');
        assert.strictEqual(
            new Domain([["name", "=", "null"]]).toString(),
            '[("name", "=", "null")]'
        );
        assert.strictEqual(
            new Domain([["name", "=", "false"]]).toString(),
            '[("name", "=", "false")]'
        );
        assert.strictEqual(
            new Domain([["name", "=", "true"]]).toString(),
            '[("name", "=", "true")]'
        );
        assert.strictEqual(new Domain().toString(), "[]");
        assert.strictEqual(
            new Domain([["name", "in", [true, false]]]).toString(),
            '[("name", "in", [True, False])]'
        );
        assert.strictEqual(
            new Domain([["name", "in", [null]]]).toString(),
            '[("name", "in", [None])]'
        );
        assert.strictEqual(
            new Domain([["name", "in", ["foo", "bar"]]]).toString(),
            '[("name", "in", ["foo", "bar"])]'
        );
        assert.strictEqual(
            new Domain([["name", "in", [1, 2]]]).toString(),
            '[("name", "in", [1, 2])]'
        );
        assert.strictEqual(
            new Domain(["&", ["name", "=", "foo"], ["type", "=", "bar"]]).toString(),
            '["&", ("name", "=", "foo"), ("type", "=", "bar")]'
        );
        assert.strictEqual(
            new Domain(["|", ["name", "=", "foo"], ["type", "=", "bar"]]).toString(),
            '["|", ("name", "=", "foo"), ("type", "=", "bar")]'
        );
        assert.strictEqual(new Domain().toString(), "[]");

        // string domains are only reformatted
        assert.strictEqual(
            new Domain('[("name","ilike","foo")]').toString(),
            '[("name", "ilike", "foo")]'
        );
    });

    QUnit.test("implicit &", function (assert) {
        const domain = new Domain([
            ["a", "=", 3],
            ["b", "=", 4],
        ]);
        assert.notOk(domain.contains({}));
        assert.ok(domain.contains({ a: 3, b: 4 }));
        assert.notOk(domain.contains({ a: 3, b: 5 }));
    });

    QUnit.test("comparison operators", function (assert) {
        assert.ok(new Domain([["a", "=", 3]]).contains({ a: 3 }));
        assert.notOk(new Domain([["a", "=", 3]]).contains({ a: 4 }));
        assert.strictEqual(new Domain([["a", "=", 3]]).toString(), `[("a", "=", 3)]`);
        assert.ok(new Domain([["a", "==", 3]]).contains({ a: 3 }));
        assert.notOk(new Domain([["a", "==", 3]]).contains({ a: 4 }));
        assert.strictEqual(new Domain([["a", "==", 3]]).toString(), `[("a", "==", 3)]`);
        assert.notOk(new Domain([["a", "!=", 3]]).contains({ a: 3 }));
        assert.ok(new Domain([["a", "!=", 3]]).contains({ a: 4 }));
        assert.strictEqual(new Domain([["a", "!=", 3]]).toString(), `[("a", "!=", 3)]`);
        assert.notOk(new Domain([["a", "<>", 3]]).contains({ a: 3 }));
        assert.ok(new Domain([["a", "<>", 3]]).contains({ a: 4 }));
        assert.strictEqual(new Domain([["a", "<>", 3]]).toString(), `[("a", "<>", 3)]`);
        assert.notOk(new Domain([["a", "<", 3]]).contains({ a: 5 }));
        assert.notOk(new Domain([["a", "<", 3]]).contains({ a: 3 }));
        assert.ok(new Domain([["a", "<", 3]]).contains({ a: 2 }));
        assert.strictEqual(new Domain([["a", "<", 3]]).toString(), `[("a", "<", 3)]`);
        assert.notOk(new Domain([["a", "<=", 3]]).contains({ a: 5 }));
        assert.ok(new Domain([["a", "<=", 3]]).contains({ a: 3 }));
        assert.ok(new Domain([["a", "<=", 3]]).contains({ a: 2 }));
        assert.strictEqual(new Domain([["a", "<=", 3]]).toString(), `[("a", "<=", 3)]`);
        assert.ok(new Domain([["a", ">", 3]]).contains({ a: 5 }));
        assert.notOk(new Domain([["a", ">", 3]]).contains({ a: 3 }));
        assert.notOk(new Domain([["a", ">", 3]]).contains({ a: 2 }));
        assert.strictEqual(new Domain([["a", ">", 3]]).toString(), `[("a", ">", 3)]`);
        assert.ok(new Domain([["a", ">=", 3]]).contains({ a: 5 }));
        assert.ok(new Domain([["a", ">=", 3]]).contains({ a: 3 }));
        assert.notOk(new Domain([["a", ">=", 3]]).contains({ a: 2 }));
        assert.strictEqual(new Domain([["a", ">=", 3]]).toString(), `[("a", ">=", 3)]`);
    });

    QUnit.test("other operators", function (assert) {
        assert.ok(new Domain([["a", "in", 3]]).contains({ a: 3 }));
        assert.ok(new Domain([["a", "in", [1, 2, 3]]]).contains({ a: 3 }));
        assert.ok(new Domain([["a", "in", [1, 2, 3]]]).contains({ a: [3] }));
        assert.notOk(new Domain([["a", "in", 3]]).contains({ a: 5 }));
        assert.notOk(new Domain([["a", "in", [1, 2, 3]]]).contains({ a: 5 }));
        assert.notOk(new Domain([["a", "in", [1, 2, 3]]]).contains({ a: [5] }));
        assert.notOk(new Domain([["a", "not in", 3]]).contains({ a: 3 }));
        assert.notOk(new Domain([["a", "not in", [1, 2, 3]]]).contains({ a: 3 }));
        assert.notOk(new Domain([["a", "not in", [1, 2, 3]]]).contains({ a: [3] }));
        assert.ok(new Domain([["a", "not in", 3]]).contains({ a: 5 }));
        assert.ok(new Domain([["a", "not in", [1, 2, 3]]]).contains({ a: 5 }));
        assert.ok(new Domain([["a", "not in", [1, 2, 3]]]).contains({ a: [5] }));
        assert.ok(new Domain([["a", "like", "abc"]]).contains({ a: "abc" }));
        assert.notOk(new Domain([["a", "like", "abc"]]).contains({ a: "def" }));
        assert.ok(new Domain([["a", "=like", "abc"]]).contains({ a: "abc" }));
        assert.notOk(new Domain([["a", "=like", "abc"]]).contains({ a: "def" }));
        assert.ok(new Domain([["a", "ilike", "abc"]]).contains({ a: "abc" }));
        assert.notOk(new Domain([["a", "ilike", "abc"]]).contains({ a: "def" }));
        assert.ok(new Domain([["a", "=ilike", "abc"]]).contains({ a: "abc" }));
        assert.notOk(new Domain([["a", "=ilike", "abc"]]).contains({ a: "def" }));
    });

    QUnit.test("creating a domain with a string expression", function (assert) {
        assert.strictEqual(new Domain(`[('a', '>=', 3)]`).toString(), `[("a", ">=", 3)]`);
        assert.ok(new Domain(`[('a', '>=', 3)]`).contains({ a: 5 }));
    });

    QUnit.test("can evaluate a python expression", function (assert) {
        assert.deepEqual(new Domain(`[('date', '!=', False)]`).toList(), [["date", "!=", false]]);
        assert.deepEqual(new Domain(`[('date', '!=', False)]`).toList(), [["date", "!=", false]]);
        assert.deepEqual(
            new Domain(`[('date', '!=', 1 + 2)]`).toString(),
            `[("date", "!=", 1 + 2)]`
        );
        assert.deepEqual(new Domain(`[('date', '!=', 1 + 2)]`).toList(), [["date", "!=", 3]]);
        assert.ok(new Domain(`[('a', '==', 1 + 2)]`).contains({ a: 3 }));
        assert.notOk(new Domain(`[('a', '==', 1 + 2)]`).contains({ a: 2 }));
    });

    QUnit.test("some expression with date stuff", function (assert) {
        patchWithCleanup(PyDate, {
            today() {
                return new PyDate(2013, 4, 24);
            },
        });
        let domainStr =
            "[('date','>=', (context_today() - datetime.timedelta(days=30)).strftime('%Y-%m-%d'))]";
        assert.deepEqual(new Domain(domainStr).toList(), [["date", ">=", "2013-03-25"]]);
        domainStr = "[('date', '>=', context_today() - relativedelta(days=30))]";
        const domainList = new Domain(domainStr).toList(); // domain creation using `parseExpr` function since the parameter is a string.
        assert.deepEqual(
            domainList[0][2],
            PyDate.create({ day: 25, month: 3, year: 2013 }),
            "The right item in the rule in the domain should be a PyDate object"
        );
        assert.deepEqual(JSON.stringify(domainList), '[["date",">=","2013-03-25"]]');
        const domainList2 = new Domain(domainList).toList(); // domain creation using `toAST` function since the parameter is a list.
        assert.deepEqual(
            domainList2[0][2],
            PyDate.create({ day: 25, month: 3, year: 2013 }),
            "The right item in the rule in the domain should be a PyDate object"
        );
        assert.deepEqual(JSON.stringify(domainList2), '[["date",">=","2013-03-25"]]');
    });

    QUnit.test("Check that there is no dependency between two domains", function (assert) {
        // The purpose of this test is to verify that a domain created on the basis
        // of another one does not share any dependency.
        const domain1 = new Domain(`[('date', '!=', False)]`);
        const domain2 = new Domain(domain1);
        assert.strictEqual(domain1.toString(), domain2.toString());

        domain2.ast.value.unshift({ type: 1, value: "!" });
        assert.notEqual(domain1.toString(), domain2.toString());
    });

    QUnit.test("TRUE and FALSE Domain", function (assert) {
        assert.ok(Domain.TRUE.contains({}));
        assert.notOk(Domain.FALSE.contains({}));

        assert.ok(Domain.and([Domain.TRUE, new Domain([["a", "=", 3]])]).contains({ a: 3 }));
        assert.notOk(Domain.and([Domain.FALSE, new Domain([["a", "=", 3]])]).contains({ a: 3 }));
    });

    QUnit.test("invalid domains should not succeed", function (assert) {
        assert.throws(
            () => new Domain(["|", ["hr_presence_state", "=", "absent"]]),
            /invalid domain .* \(missing 1 segment/
        );
        assert.throws(
            () =>
                new Domain([
                    "|",
                    "|",
                    ["hr_presence_state", "=", "absent"],
                    ["attendance_state", "=", "checked_in"],
                ]),
            /invalid domain .* \(missing 1 segment/
        );
        assert.throws(
            () => new Domain(["|", "|", ["hr_presence_state", "=", "absent"]]),
            /invalid domain .* \(missing 2 segment\(s\)/
        );
        assert.throws(
            () => new Domain(["&", ["composition_mode", "!=", "mass_post"]]),
            /invalid domain .* \(missing 1 segment/
        );
        assert.throws(() => new Domain(["!"]), /invalid domain .* \(missing 1 segment/);
    });

    QUnit.test("follow relations", function (assert) {
        assert.ok(
            new Domain([["partner.city", "ilike", "Bru"]]).contains({
                name: "Lucas",
                partner: {
                    city: "Bruxelles",
                },
            })
        );
        assert.ok(
            new Domain([["partner.city.name", "ilike", "Bru"]]).contains({
                name: "Lucas",
                partner: {
                    city: {
                        name: "Bruxelles",
                    },
                },
            })
        );
    });

    QUnit.test("Arrays comparison", (assert) => {
        const domain = new Domain(["&", ["a", "==", []], ["b", "!=", []]]);

        assert.ok(domain.contains({ a: [] }));
        assert.ok(domain.contains({ a: [], b: [4] }));
        assert.notOk(domain.contains({ a: [1] }));
        assert.notOk(domain.contains({ b: [] }));
    });

    // ---------------------------------------------------------------------------
    // Normalization
    // ---------------------------------------------------------------------------
    QUnit.module("Normalization");

    QUnit.test("return simple (normalized) domains", function (assert) {
        const domains = ["[]", `[("a", "=", 1)]`, `["!", ("a", "=", 1)]`];
        for (const domain of domains) {
            assert.strictEqual(new Domain(domain).toString(), domain);
        }
    });

    QUnit.test("properly add the & in a non normalized domain", function (assert) {
        assert.strictEqual(
            new Domain(`[("a", "=", 1), ("b", "=", 2)]`).toString(),
            `["&", ("a", "=", 1), ("b", "=", 2)]`
        );
    });

    QUnit.test("normalize domain with ! operator", function (assert) {
        assert.strictEqual(
            new Domain(`["!", ("a", "=", 1), ("b", "=", 2)]`).toString(),
            `["&", "!", ("a", "=", 1), ("b", "=", 2)]`
        );
    });

    // ---------------------------------------------------------------------------
    // Combining domains
    // ---------------------------------------------------------------------------
    QUnit.module("Combining domains");

    QUnit.test("combining zero domain", function (assert) {
        assert.strictEqual(Domain.combine([], "AND").toString(), "[]");
        assert.strictEqual(Domain.combine([], "OR").toString(), "[]");
        assert.ok(Domain.combine([], "AND").contains({ a: 1, b: 2 }));
    });

    QUnit.test("combining one domain", function (assert) {
        assert.strictEqual(
            Domain.combine([`[("a", "=", 1)]`], "AND").toString(),
            `[("a", "=", 1)]`
        );
        assert.strictEqual(
            Domain.combine([`[("user_id", "=", uid)]`], "AND").toString(),
            `[("user_id", "=", uid)]`
        );
        assert.strictEqual(Domain.combine([[["a", "=", 1]]], "AND").toString(), `[("a", "=", 1)]`);
        assert.strictEqual(
            Domain.combine(["[('a', '=', '1'), ('b', '!=', 2)]"], "AND").toString(),
            `["&", ("a", "=", "1"), ("b", "!=", 2)]`
        );
    });

    QUnit.test("combining two domains", function (assert) {
        assert.strictEqual(
            Domain.combine([`[("a", "=", 1)]`, "[]"], "AND").toString(),
            `[("a", "=", 1)]`
        );
        assert.strictEqual(
            Domain.combine([`[("a", "=", 1)]`, []], "AND").toString(),
            `[("a", "=", 1)]`
        );
        assert.strictEqual(
            Domain.combine([new Domain(`[("a", "=", 1)]`), "[]"], "AND").toString(),
            `[("a", "=", 1)]`
        );
        assert.strictEqual(
            Domain.combine([new Domain(`[("a", "=", 1)]`), "[]"], "OR").toString(),
            `[("a", "=", 1)]`
        );
        assert.strictEqual(
            Domain.combine([[["a", "=", 1]], "[('uid', '<=', uid)]"], "AND").toString(),
            `["&", ("a", "=", 1), ("uid", "<=", uid)]`
        );
        assert.strictEqual(
            Domain.combine([[["a", "=", 1]], "[('b', '<=', 3)]"], "OR").toString(),
            `["|", ("a", "=", 1), ("b", "<=", 3)]`
        );
        assert.strictEqual(
            Domain.combine(
                ["[('a', '=', '1'), ('c', 'in', [4, 5])]", "[('b', '<=', 3)]"],
                "OR"
            ).toString(),
            `["|", "&", ("a", "=", "1"), ("c", "in", [4, 5]), ("b", "<=", 3)]`
        );
        assert.strictEqual(
            Domain.combine(
                [new Domain("[('a', '=', '1'), ('c', 'in', [4, 5])]"), "[('b', '<=', 3)]"],
                "OR"
            ).toString(),
            `["|", "&", ("a", "=", "1"), ("c", "in", [4, 5]), ("b", "<=", 3)]`
        );
    });

    QUnit.test("combining three domains", function (assert) {
        assert.strictEqual(
            Domain.combine(
                [
                    new Domain("[('a', '=', '1'), ('c', 'in', [4, 5])]"),
                    [["b", "<=", 3]],
                    `['!', ('uid', '=', uid)]`,
                ],
                "OR"
            ).toString(),
            `["|", "&", ("a", "=", "1"), ("c", "in", [4, 5]), "|", ("b", "<=", 3), "!", ("uid", "=", uid)]`
        );
    });

    // ---------------------------------------------------------------------------
    // OPERATOR AND / OR / NOT
    // ---------------------------------------------------------------------------
    QUnit.module("Operator and/or/not");
    QUnit.test("combining two domains with and/or", function (assert) {
        assert.strictEqual(Domain.and([`[("a", "=", 1)]`, "[]"]).toString(), `[("a", "=", 1)]`);
        assert.strictEqual(Domain.and([`[("a", "=", 1)]`, []]).toString(), `[("a", "=", 1)]`);
        assert.strictEqual(
            Domain.and([new Domain(`[("a", "=", 1)]`), "[]"]).toString(),
            `[("a", "=", 1)]`
        );
        assert.strictEqual(
            Domain.or([new Domain(`[("a", "=", 1)]`), "[]"]).toString(),
            `[("a", "=", 1)]`
        );
        assert.strictEqual(
            Domain.and([[["a", "=", 1]], "[('uid', '<=', uid)]"]).toString(),
            `["&", ("a", "=", 1), ("uid", "<=", uid)]`
        );
        assert.strictEqual(
            Domain.or([[["a", "=", 1]], "[('b', '<=', 3)]"]).toString(),
            `["|", ("a", "=", 1), ("b", "<=", 3)]`
        );
        assert.strictEqual(
            Domain.or(["[('a', '=', '1'), ('c', 'in', [4, 5])]", "[('b', '<=', 3)]"]).toString(),
            `["|", "&", ("a", "=", "1"), ("c", "in", [4, 5]), ("b", "<=", 3)]`
        );
        assert.strictEqual(
            Domain.or([
                new Domain("[('a', '=', '1'), ('c', 'in', [4, 5])]"),
                "[('b', '<=', 3)]",
            ]).toString(),
            `["|", "&", ("a", "=", "1"), ("c", "in", [4, 5]), ("b", "<=", 3)]`
        );
    });

    QUnit.test("apply `NOT` on a Domain", function (assert) {
        assert.strictEqual(Domain.not("[('a', '=', 1)]").toString(), `["!", ("a", "=", 1)]`);
        assert.strictEqual(
            Domain.not('[("uid", "<=", uid)]').toString(),
            `["!", ("uid", "<=", uid)]`
        );
        assert.strictEqual(
            Domain.not(new Domain("[('a', '=', 1)]")).toString(),
            `["!", ("a", "=", 1)]`
        );
        assert.strictEqual(
            Domain.not(new Domain([["a", "=", 1]])).toString(),
            `["!", ("a", "=", 1)]`
        );
    });

    QUnit.test("tuple are supported", (assert) => {
        assert.deepEqual(
            new Domain(`(("field", "like", "string"), ("field", "like", "strOng"))`).toList(),
            ["&", ["field", "like", "string"], ["field", "like", "strOng"]]
        );
        assert.deepEqual(new Domain(`("!",("field", "like", "string"))`).toList(), [
            "!",
            ["field", "like", "string"],
        ]);
        assert.throws(() => new Domain(`(("field", "like", "string"))`), /Invalid domain AST/);
        assert.throws(() => new Domain(`("&", "&", "|")`), /Invalid domain AST/);
        assert.throws(() => new Domain(`("&", "&", 3)`), /Invalid domain AST/);
    });
});
