import { describe, expect, test } from "@odoo/hoot";

import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Domain } from "@web/core/domain";
import { PyDate } from "@web/core/py_js/py_date";

describe.current.tags("headless");

//-------------------------------------------------------------------------
// Basic properties
//-------------------------------------------------------------------------

describe("Basic Properties", () => {
    test("empty", () => {
        expect(new Domain([]).contains({})).toBe(true);
        expect(new Domain([]).toString()).toBe("[]");
        expect(new Domain([]).toList()).toEqual([]);
    });

    test("undefined domain", () => {
        expect(new Domain(undefined).contains({})).toBe(true);
        expect(new Domain(undefined).toString()).toBe("[]");
        expect(new Domain(undefined).toList()).toEqual([]);
    });

    test("simple condition", () => {
        expect(new Domain([["a", "=", 3]]).contains({ a: 3 })).toBe(true);
        expect(new Domain([["a", "=", 3]]).contains({ a: 5 })).toBe(false);
        expect(new Domain([["a", "=", 3]]).toString()).toBe(`[("a", "=", 3)]`);
        expect(new Domain([["a", "=", 3]]).toList()).toEqual([["a", "=", 3]]);
    });

    test("can be created from domain", () => {
        const domain = new Domain([["a", "=", 3]]);
        expect(new Domain(domain).toString()).toBe(`[("a", "=", 3)]`);
    });

    test("basic", () => {
        const record = {
            a: 3,
            group_method: "line",
            select1: "day",
            rrule_type: "monthly",
        };
        expect(new Domain([["a", "=", 3]]).contains(record)).toBe(true);
        expect(new Domain([["a", "=", 5]]).contains(record)).toBe(false);
        expect(new Domain([["group_method", "!=", "count"]]).contains(record)).toBe(true);
        expect(
            new Domain([
                ["select1", "=", "day"],
                ["rrule_type", "=", "monthly"],
            ]).contains(record)
        ).toBe(true);
    });

    test("support of '=?' operator", () => {
        const record = { a: 3 };
        expect(new Domain([["a", "=?", null]]).contains(record)).toBe(true);
        expect(new Domain([["a", "=?", false]]).contains(record)).toBe(true);
        expect(new Domain(["!", ["a", "=?", false]]).contains(record)).toBe(false);
        expect(new Domain([["a", "=?", 1]]).contains(record)).toBe(false);
        expect(new Domain([["a", "=?", 3]]).contains(record)).toBe(true);
        expect(new Domain(["!", ["a", "=?", 3]]).contains(record)).toBe(false);
    });

    test("or", () => {
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
        expect(new Domain(currentDomain).contains({ ...record, section_id: 42 })).toBe(true);
        expect(new Domain(currentDomain).contains({ ...record, user_id: 3 })).toBe(true);
        expect(new Domain(currentDomain).contains({ ...record, member_ids: 3 })).toBe(true);
    });

    test("and", () => {
        const domain = new Domain(["&", "&", ["a", "=", 1], ["b", "=", 2], ["c", "=", 3]]);

        expect(domain.contains({ a: 1, b: 2, c: 3 })).toBe(true);
        expect(domain.contains({ a: -1, b: 2, c: 3 })).toBe(false);
        expect(domain.contains({ a: 1, b: -1, c: 3 })).toBe(false);
        expect(domain.contains({ a: 1, b: 2, c: -1 })).toBe(false);
    });

    test("not", () => {
        const record = {
            a: 5,
            group_method: "line",
        };
        expect(new Domain(["!", ["a", "=", 3]]).contains(record)).toBe(true);
        expect(new Domain(["!", ["group_method", "=", "count"]]).contains(record)).toBe(true);
    });

    test("like, =like, ilike, =ilike and not likes", () => {
        expect.assertions(34);

        expect(new Domain([["a", "like", "value"]]).contains({ a: "value" })).toBe(true);
        expect(new Domain([["a", "like", "value"]]).contains({ a: "some value" })).toBe(true);
        expect(new Domain([["a", "like", "value"]]).contains({ a: "Some Value" })).not.toBe(true);
        expect(new Domain([["a", "like", "value"]]).contains({ a: false })).toBe(false);

        expect(new Domain([["a", "=like", "%value"]]).contains({ a: "value" })).toBe(true);
        expect(new Domain([["a", "=like", "%value"]]).contains({ a: "some value" })).toBe(true);
        expect(new Domain([["a", "=like", "%value"]]).contains({ a: "Some Value" })).not.toBe(true);
        expect(new Domain([["a", "=like", "%value"]]).contains({ a: false })).toBe(false);

        expect(new Domain([["a", "ilike", "value"]]).contains({ a: "value" })).toBe(true);
        expect(new Domain([["a", "ilike", "value"]]).contains({ a: "some value" })).toBe(true);
        expect(new Domain([["a", "ilike", "value"]]).contains({ a: "Some Value" })).toBe(true);
        expect(new Domain([["a", "ilike", "value"]]).contains({ a: false })).toBe(false);

        expect(new Domain([["a", "=ilike", "%value"]]).contains({ a: "value" })).toBe(true);
        expect(new Domain([["a", "=ilike", "%value"]]).contains({ a: "some value" })).toBe(true);
        expect(new Domain([["a", "=ilike", "%value"]]).contains({ a: "Some Value" })).toBe(true);
        expect(new Domain([["a", "=ilike", "%value"]]).contains({ a: false })).toBe(false);

        expect(new Domain([["a", "not like", "value"]]).contains({ a: "value" })).not.toBe(true);
        expect(new Domain([["a", "not like", "value"]]).contains({ a: "some value" })).not.toBe(
            true
        );
        expect(new Domain([["a", "not like", "value"]]).contains({ a: "Some Value" })).toBe(true);
        expect(new Domain([["a", "not like", "value"]]).contains({ a: "something" })).toBe(true);
        expect(new Domain([["a", "not like", "value"]]).contains({ a: "Something" })).toBe(true);
        expect(new Domain([["a", "not like", "value"]]).contains({ a: false })).toBe(true);

        expect(new Domain([["a", "not ilike", "value"]]).contains({ a: "value" })).not.toBe(true);
        expect(new Domain([["a", "not ilike", "value"]]).contains({ a: "some value" })).toBe(false);
        expect(new Domain([["a", "not ilike", "value"]]).contains({ a: "Some Value" })).toBe(false);
        expect(new Domain([["a", "not ilike", "value"]]).contains({ a: "something" })).toBe(true);
        expect(new Domain([["a", "not ilike", "value"]]).contains({ a: "Something" })).toBe(true);
        expect(new Domain([["a", "not ilike", "value"]]).contains({ a: false })).toBe(true);

        expect(new Domain([["a", "not =like", "%value"]]).contains({ a: "some value" })).toBe(false);
        expect(new Domain([["a", "not =like", "%value"]]).contains({ a: "Some Value" })).not.toBe(false);

        expect(new Domain([["a", "not =ilike", "%value"]]).contains({ a: "value" })).toBe(false);
        expect(new Domain([["a", "not =ilike", "%value"]]).contains({ a: "some value" })).toBe(false);
        expect(new Domain([["a", "not =ilike", "%value"]]).contains({ a: "Some Value" })).toBe(false);
        expect(new Domain([["a", "not =ilike", "%value"]]).contains({ a: false })).toBe(true);
    });

    test("complex domain", () => {
        const domain = new Domain(["&", "!", ["a", "=", 1], "|", ["a", "=", 2], ["a", "=", 3]]);

        expect(domain.contains({ a: 1 })).toBe(false);
        expect(domain.contains({ a: 2 })).toBe(true);
        expect(domain.contains({ a: 3 })).toBe(true);
        expect(domain.contains({ a: 4 })).toBe(false);
    });

    test("toList", () => {
        expect(new Domain([]).toList()).toEqual([]);
        expect(new Domain([["a", "=", 3]]).toList()).toEqual([["a", "=", 3]]);
        expect(
            new Domain([
                ["a", "=", 3],
                ["b", "!=", "4"],
            ]).toList()
        ).toEqual(["&", ["a", "=", 3], ["b", "!=", "4"]]);
        expect(new Domain(["!", ["a", "=", 3]]).toList()).toEqual(["!", ["a", "=", 3]]);
    });

    test("toString", () => {
        expect(new Domain([]).toString()).toBe(`[]`);
        expect(new Domain([["a", "=", 3]]).toString()).toBe(`[("a", "=", 3)]`);
        expect(
            new Domain([
                ["a", "=", 3],
                ["b", "!=", "4"],
            ]).toString()
        ).toBe(`["&", ("a", "=", 3), ("b", "!=", "4")]`);
        expect(new Domain(["!", ["a", "=", 3]]).toString()).toBe(`["!", ("a", "=", 3)]`);
        expect(new Domain([["name", "=", null]]).toString()).toBe('[("name", "=", None)]');
        expect(new Domain([["name", "=", false]]).toString()).toBe('[("name", "=", False)]');
        expect(new Domain([["name", "=", true]]).toString()).toBe('[("name", "=", True)]');
        expect(new Domain([["name", "=", "null"]]).toString()).toBe('[("name", "=", "null")]');
        expect(new Domain([["name", "=", "false"]]).toString()).toBe('[("name", "=", "false")]');
        expect(new Domain([["name", "=", "true"]]).toString()).toBe('[("name", "=", "true")]');
        expect(new Domain().toString()).toBe("[]");
        expect(new Domain([["name", "in", [true, false]]]).toString()).toBe(
            '[("name", "in", [True, False])]'
        );
        expect(new Domain([["name", "in", [null]]]).toString()).toBe('[("name", "in", [None])]');
        expect(new Domain([["name", "in", ["foo", "bar"]]]).toString()).toBe(
            '[("name", "in", ["foo", "bar"])]'
        );
        expect(new Domain([["name", "in", [1, 2]]]).toString()).toBe('[("name", "in", [1, 2])]');
        expect(new Domain(["&", ["name", "=", "foo"], ["type", "=", "bar"]]).toString()).toBe(
            '["&", ("name", "=", "foo"), ("type", "=", "bar")]'
        );
        expect(new Domain(["|", ["name", "=", "foo"], ["type", "=", "bar"]]).toString()).toBe(
            '["|", ("name", "=", "foo"), ("type", "=", "bar")]'
        );
        expect(new Domain().toString()).toBe("[]");

        // string domains are only reformatted
        expect(new Domain('[("name","ilike","foo")]').toString()).toBe(
            '[("name", "ilike", "foo")]'
        );
    });

    test("toJson", () => {
        expect(new Domain([]).toJson()).toEqual([]);
        expect(new Domain("[]").toJson()).toEqual([]);
        expect(new Domain([["a", "=", 3]]).toJson()).toEqual([["a", "=", 3]]);
        expect(new Domain('[("a", "=", 3)]').toJson()).toEqual([["a", "=", 3]]);
        expect(new Domain('[("user_id", "=", uid)]').toJson()).toBe('[("user_id", "=", uid)]');
        expect(new Domain('[("date", "=", context_today())]').toJson()).toBe(
            '[("date", "=", context_today())]'
        );
    });

    test("implicit &", () => {
        const domain = new Domain([
            ["a", "=", 3],
            ["b", "=", 4],
        ]);
        expect(domain.contains({})).toBe(false);
        expect(domain.contains({ a: 3, b: 4 })).toBe(true);
        expect(domain.contains({ a: 3, b: 5 })).toBe(false);
    });

    test("comparison operators", () => {
        expect(new Domain([["a", "=", 3]]).contains({ a: 3 })).toBe(true);
        expect(new Domain([["a", "=", 3]]).contains({ a: 4 })).toBe(false);
        expect(new Domain([["a", "=", 3]]).toString()).toBe(`[("a", "=", 3)]`);
        expect(new Domain([["a", "==", 3]]).contains({ a: 3 })).toBe(true);
        expect(new Domain([["a", "==", 3]]).contains({ a: 4 })).toBe(false);
        expect(new Domain([["a", "==", 3]]).toString()).toBe(`[("a", "==", 3)]`);
        expect(new Domain([["a", "!=", 3]]).contains({ a: 3 })).toBe(false);
        expect(new Domain([["a", "!=", 3]]).contains({ a: 4 })).toBe(true);
        expect(new Domain([["a", "!=", 3]]).toString()).toBe(`[("a", "!=", 3)]`);
        expect(new Domain([["a", "<>", 3]]).contains({ a: 3 })).toBe(false);
        expect(new Domain([["a", "<>", 3]]).contains({ a: 4 })).toBe(true);
        expect(new Domain([["a", "<>", 3]]).toString()).toBe(`[("a", "<>", 3)]`);
        expect(new Domain([["a", "<", 3]]).contains({ a: 5 })).toBe(false);
        expect(new Domain([["a", "<", 3]]).contains({ a: 3 })).toBe(false);
        expect(new Domain([["a", "<", 3]]).contains({ a: 2 })).toBe(true);
        expect(new Domain([["a", "<", 3]]).toString()).toBe(`[("a", "<", 3)]`);
        expect(new Domain([["a", "<=", 3]]).contains({ a: 5 })).toBe(false);
        expect(new Domain([["a", "<=", 3]]).contains({ a: 3 })).toBe(true);
        expect(new Domain([["a", "<=", 3]]).contains({ a: 2 })).toBe(true);
        expect(new Domain([["a", "<=", 3]]).toString()).toBe(`[("a", "<=", 3)]`);
        expect(new Domain([["a", ">", 3]]).contains({ a: 5 })).toBe(true);
        expect(new Domain([["a", ">", 3]]).contains({ a: 3 })).toBe(false);
        expect(new Domain([["a", ">", 3]]).contains({ a: 2 })).toBe(false);
        expect(new Domain([["a", ">", 3]]).toString()).toBe(`[("a", ">", 3)]`);
        expect(new Domain([["a", ">=", 3]]).contains({ a: 5 })).toBe(true);
        expect(new Domain([["a", ">=", 3]]).contains({ a: 3 })).toBe(true);
        expect(new Domain([["a", ">=", 3]]).contains({ a: 2 })).toBe(false);
        expect(new Domain([["a", ">=", 3]]).toString()).toBe(`[("a", ">=", 3)]`);
    });

    test("other operators", () => {
        expect(new Domain([["a", "in", 3]]).contains({ a: 3 })).toBe(true);
        expect(new Domain([["a", "in", [1, 2, 3]]]).contains({ a: 3 })).toBe(true);
        expect(new Domain([["a", "in", [1, 2, 3]]]).contains({ a: [3] })).toBe(true);
        expect(new Domain([["a", "in", 3]]).contains({ a: 5 })).toBe(false);
        expect(new Domain([["a", "in", [1, 2, 3]]]).contains({ a: 5 })).toBe(false);
        expect(new Domain([["a", "in", [1, 2, 3]]]).contains({ a: [5] })).toBe(false);
        expect(new Domain([["a", "not in", 3]]).contains({ a: 3 })).toBe(false);
        expect(new Domain([["a", "not in", [1, 2, 3]]]).contains({ a: 3 })).toBe(false);
        expect(new Domain([["a", "not in", [1, 2, 3]]]).contains({ a: [3] })).toBe(false);
        expect(new Domain([["a", "not in", 3]]).contains({ a: 5 })).toBe(true);
        expect(new Domain([["a", "not in", [1, 2, 3]]]).contains({ a: 5 })).toBe(true);
        expect(new Domain([["a", "not in", [1, 2, 3]]]).contains({ a: [5] })).toBe(true);
        expect(new Domain([["a", "like", "abc"]]).contains({ a: "abc" })).toBe(true);
        expect(new Domain([["a", "like", "abc"]]).contains({ a: "def" })).toBe(false);
        expect(new Domain([["a", "=like", "abc"]]).contains({ a: "abc" })).toBe(true);
        expect(new Domain([["a", "=like", "abc"]]).contains({ a: "def" })).toBe(false);
        expect(new Domain([["a", "ilike", "abc"]]).contains({ a: "abc" })).toBe(true);
        expect(new Domain([["a", "ilike", "abc"]]).contains({ a: "def" })).toBe(false);
        expect(new Domain([["a", "=ilike", "abc"]]).contains({ a: "abc" })).toBe(true);
        expect(new Domain([["a", "=ilike", "abc"]]).contains({ a: "def" })).toBe(false);
    });

    test("creating a domain with a string expression", () => {
        expect(new Domain(`[('a', '>=', 3)]`).toString()).toBe(`[("a", ">=", 3)]`);
        expect(new Domain(`[('a', '>=', 3)]`).contains({ a: 5 })).toBe(true);
    });

    test("can evaluate a python expression", () => {
        expect(new Domain(`[('date', '!=', False)]`).toList()).toEqual([["date", "!=", false]]);
        expect(new Domain(`[('date', '!=', False)]`).toList()).toEqual([["date", "!=", false]]);
        expect(new Domain(`[('date', '!=', 1 + 2)]`).toString()).toBe(`[("date", "!=", 1 + 2)]`);
        expect(new Domain(`[('date', '!=', 1 + 2)]`).toList()).toEqual([["date", "!=", 3]]);
        expect(new Domain(`[('a', '==', 1 + 2)]`).contains({ a: 3 })).toBe(true);
        expect(new Domain(`[('a', '==', 1 + 2)]`).contains({ a: 2 })).toBe(false);
    });

    test("some expression with date stuff", () => {
        patchWithCleanup(PyDate, {
            today() {
                return new PyDate(2013, 4, 24);
            },
        });

        expect(
            new Domain(
                "[('date','>=', (context_today() - datetime.timedelta(days=30)).strftime('%Y-%m-%d'))]"
            ).toList()
        ).toEqual([["date", ">=", "2013-03-25"]]);

        const domainList = new Domain(
            "[('date', '>=', context_today() - relativedelta(days=30))]"
        ).toList(); // domain creation using `parseExpr` function since the parameter is a string.

        expect(domainList[0][2]).toEqual(PyDate.create({ day: 25, month: 3, year: 2013 }), {
            message: "The right item in the rule in the domain should be a PyDate object",
        });
        expect(JSON.stringify(domainList)).toBe('[["date",">=","2013-03-25"]]');

        const domainList2 = new Domain(domainList).toList(); // domain creation using `toAST` function since the parameter is a list.
        expect(domainList2[0][2]).toEqual(PyDate.create({ day: 25, month: 3, year: 2013 }), {
            message: "The right item in the rule in the domain should be a PyDate object",
        });
        expect(JSON.stringify(domainList2)).toBe('[["date",">=","2013-03-25"]]');
    });

    test("Check that there is no dependency between two domains", () => {
        // The purpose of this test is to verify that a domain created on the basis
        // of another one does not share any dependency.
        const domain1 = new Domain(`[('date', '!=', False)]`);
        const domain2 = new Domain(domain1);
        expect(domain1.toString()).toBe(domain2.toString());

        domain2.ast.value.unshift({ type: 1, value: "!" });
        expect(domain1.toString()).not.toBe(domain2.toString());
    });

    test("TRUE and FALSE Domain", () => {
        expect(Domain.TRUE.contains({})).toBe(true);
        expect(Domain.FALSE.contains({})).toBe(false);

        expect(Domain.and([Domain.TRUE, new Domain([["a", "=", 3]])]).contains({ a: 3 })).toBe(
            true
        );
        expect(Domain.and([Domain.FALSE, new Domain([["a", "=", 3]])]).contains({ a: 3 })).toBe(
            false
        );
    });

    test("invalid domains should not succeed", () => {
        expect(() => new Domain(["|", ["hr_presence_state", "=", "absent"]])).toThrow(
            /invalid domain .* \(missing 1 segment/
        );
        expect(
            () =>
                new Domain([
                    "|",
                    "|",
                    ["hr_presence_state", "=", "absent"],
                    ["attendance_state", "=", "checked_in"],
                ])
        ).toThrow(/invalid domain .* \(missing 1 segment/);
        expect(() => new Domain(["|", "|", ["hr_presence_state", "=", "absent"]])).toThrow(
            /invalid domain .* \(missing 2 segment\(s\)/
        );
        expect(() => new Domain(["&", ["composition_mode", "!=", "mass_post"]])).toThrow(
            /invalid domain .* \(missing 1 segment/
        );
        expect(() => new Domain(["!"])).toThrow(/invalid domain .* \(missing 1 segment/);
        expect(() => new Domain(`[(1, 2)]`)).toThrow(/Invalid domain AST/);
        expect(() => new Domain(`[(1, 2, 3, 4)]`)).toThrow(/Invalid domain AST/);
        expect(() => new Domain(`["a"]`)).toThrow(/Invalid domain AST/);
        expect(() => new Domain(`[1]`)).toThrow(/Invalid domain AST/);
        expect(() => new Domain(`[x]`)).toThrow(/Invalid domain AST/);
        expect(() => new Domain(`[True]`)).toThrow(/Invalid domain AST/); // will possibly change with CHM work
        expect(() => new Domain(`[(x.=, "=", 1)]`)).toThrow(/Invalid domain representation/);
        expect(() => new Domain(`[(+, "=", 1)]`)).toThrow(/Invalid domain representation/);
        expect(() => new Domain([{}])).toThrow(/Invalid domain representation/);
        expect(() => new Domain([1])).toThrow(/Invalid domain representation/);
    });

    test("follow relations", () => {
        expect(
            new Domain([["partner.city", "ilike", "Bru"]]).contains({
                name: "Lucas",
                partner: {
                    city: "Bruxelles",
                },
            })
        ).toBe(true);
        expect(
            new Domain([["partner.city.name", "ilike", "Bru"]]).contains({
                name: "Lucas",
                partner: {
                    city: {
                        name: "Bruxelles",
                    },
                },
            })
        ).toBe(true);
    });

    test("Arrays comparison", () => {
        const domain = new Domain(["&", ["a", "==", []], ["b", "!=", []]]);

        expect(domain.contains({ a: [] })).toBe(true);
        expect(domain.contains({ a: [], b: [4] })).toBe(true);
        expect(domain.contains({ a: [1] })).toBe(false);
        expect(domain.contains({ b: [] })).toBe(false);
    });
});

// ---------------------------------------------------------------------------
// Normalization
// ---------------------------------------------------------------------------
describe("Normalization", () => {
    test("return simple (normalized) domains", () => {
        const domains = ["[]", `[("a", "=", 1)]`, `["!", ("a", "=", 1)]`];
        for (const domain of domains) {
            expect(new Domain(domain).toString()).toBe(domain);
        }
    });

    test("properly add the & in a non normalized domain", () => {
        expect(new Domain(`[("a", "=", 1), ("b", "=", 2)]`).toString()).toBe(
            `["&", ("a", "=", 1), ("b", "=", 2)]`
        );
    });

    test("normalize domain with ! operator", () => {
        expect(new Domain(`["!", ("a", "=", 1), ("b", "=", 2)]`).toString()).toBe(
            `["&", "!", ("a", "=", 1), ("b", "=", 2)]`
        );
    });
});

// ---------------------------------------------------------------------------
// Combining domains
// ---------------------------------------------------------------------------
describe("Combining domains", () => {
    test("combining zero domain", () => {
        expect(Domain.combine([], "AND").toString()).toBe("[]");
        expect(Domain.combine([], "OR").toString()).toBe("[]");
        expect(Domain.combine([], "AND").contains({ a: 1, b: 2 })).toBe(true);
    });

    test("combining one domain", () => {
        expect(Domain.combine([`[("a", "=", 1)]`], "AND").toString()).toBe(`[("a", "=", 1)]`);
        expect(Domain.combine([`[("user_id", "=", uid)]`], "AND").toString()).toBe(
            `[("user_id", "=", uid)]`
        );
        expect(Domain.combine([[["a", "=", 1]]], "AND").toString()).toBe(`[("a", "=", 1)]`);
        expect(Domain.combine(["[('a', '=', '1'), ('b', '!=', 2)]"], "AND").toString()).toBe(
            `["&", ("a", "=", "1"), ("b", "!=", 2)]`
        );
    });

    test("combining two domains", () => {
        expect(Domain.combine([`[("a", "=", 1)]`, "[]"], "AND").toString()).toBe(`[("a", "=", 1)]`);
        expect(Domain.combine([`[("a", "=", 1)]`, []], "AND").toString()).toBe(`[("a", "=", 1)]`);
        expect(Domain.combine([new Domain(`[("a", "=", 1)]`), "[]"], "AND").toString()).toBe(
            `[("a", "=", 1)]`
        );
        expect(Domain.combine([new Domain(`[("a", "=", 1)]`), "[]"], "OR").toString()).toBe(
            `[("a", "=", 1)]`
        );
        expect(Domain.combine([[["a", "=", 1]], "[('uid', '<=', uid)]"], "AND").toString()).toBe(
            `["&", ("a", "=", 1), ("uid", "<=", uid)]`
        );
        expect(Domain.combine([[["a", "=", 1]], "[('b', '<=', 3)]"], "OR").toString()).toBe(
            `["|", ("a", "=", 1), ("b", "<=", 3)]`
        );
        expect(
            Domain.combine(
                ["[('a', '=', '1'), ('c', 'in', [4, 5])]", "[('b', '<=', 3)]"],
                "OR"
            ).toString()
        ).toBe(`["|", "&", ("a", "=", "1"), ("c", "in", [4, 5]), ("b", "<=", 3)]`);
        expect(
            Domain.combine(
                [new Domain("[('a', '=', '1'), ('c', 'in', [4, 5])]"), "[('b', '<=', 3)]"],
                "OR"
            ).toString()
        ).toBe(`["|", "&", ("a", "=", "1"), ("c", "in", [4, 5]), ("b", "<=", 3)]`);
    });

    test("combining three domains", () => {
        expect(
            Domain.combine(
                [
                    new Domain("[('a', '=', '1'), ('c', 'in', [4, 5])]"),
                    [["b", "<=", 3]],
                    `['!', ('uid', '=', uid)]`,
                ],
                "OR"
            ).toString()
        ).toBe(
            `["|", "&", ("a", "=", "1"), ("c", "in", [4, 5]), "|", ("b", "<=", 3), "!", ("uid", "=", uid)]`
        );
    });
});

// ---------------------------------------------------------------------------
// OPERATOR AND / OR / NOT
// ---------------------------------------------------------------------------
describe("Operator and - or - not", () => {
    test("combining two domains with and/or", () => {
        expect(Domain.and([`[("a", "=", 1)]`, "[]"]).toString()).toBe(`[("a", "=", 1)]`);
        expect(Domain.and([`[("a", "=", 1)]`, []]).toString()).toBe(`[("a", "=", 1)]`);
        expect(Domain.and([new Domain(`[("a", "=", 1)]`), "[]"]).toString()).toBe(
            `[("a", "=", 1)]`
        );
        expect(Domain.or([new Domain(`[("a", "=", 1)]`), "[]"]).toString()).toBe(`[("a", "=", 1)]`);
        expect(Domain.and([[["a", "=", 1]], "[('uid', '<=', uid)]"]).toString()).toBe(
            `["&", ("a", "=", 1), ("uid", "<=", uid)]`
        );
        expect(Domain.or([[["a", "=", 1]], "[('b', '<=', 3)]"]).toString()).toBe(
            `["|", ("a", "=", 1), ("b", "<=", 3)]`
        );
        expect(
            Domain.or(["[('a', '=', '1'), ('c', 'in', [4, 5])]", "[('b', '<=', 3)]"]).toString()
        ).toBe(`["|", "&", ("a", "=", "1"), ("c", "in", [4, 5]), ("b", "<=", 3)]`);
        expect(
            Domain.or([
                new Domain("[('a', '=', '1'), ('c', 'in', [4, 5])]"),
                "[('b', '<=', 3)]",
            ]).toString()
        ).toBe(`["|", "&", ("a", "=", "1"), ("c", "in", [4, 5]), ("b", "<=", 3)]`);
    });

    test("apply `NOT` on a Domain", () => {
        expect(Domain.not("[('a', '=', 1)]").toString()).toBe(`["!", ("a", "=", 1)]`);
        expect(Domain.not('[("uid", "<=", uid)]').toString()).toBe(`["!", ("uid", "<=", uid)]`);
        expect(Domain.not(new Domain("[('a', '=', 1)]")).toString()).toBe(`["!", ("a", "=", 1)]`);
        expect(Domain.not(new Domain([["a", "=", 1]])).toString()).toBe(`["!", ("a", "=", 1)]`);
    });

    test("tuple are supported", () => {
        expect(
            new Domain(`(("field", "like", "string"), ("field", "like", "strOng"))`).toList()
        ).toEqual(["&", ["field", "like", "string"], ["field", "like", "strOng"]]);
        expect(new Domain(`("!",("field", "like", "string"))`).toList()).toEqual([
            "!",
            ["field", "like", "string"],
        ]);
        expect(() => new Domain(`(("field", "like", "string"))`)).toThrow(/Invalid domain AST/);
        expect(() => new Domain(`("&", "&", "|")`)).toThrow(/Invalid domain AST/);
        expect(() => new Domain(`("&", "&", 3)`)).toThrow(/Invalid domain AST/);
    });
});

describe("Remove domain leaf", () => {
    test("Remove leaf in domain.", () => {
        let domain = [
            ["start_datetime", "!=", false],
            ["end_datetime", "!=", false],
            ["sale_line_id", "!=", false],
        ];
        const keysToRemove = ["start_datetime", "end_datetime"];
        let newDomain = Domain.removeDomainLeaves(domain, keysToRemove);
        let expectedDomain = new Domain([
            "&",
            ...Domain.TRUE.toList({}),
            ...Domain.TRUE.toList({}),
            ["sale_line_id", "!=", false],
        ]);
        expect(newDomain.toList({})).toEqual(expectedDomain.toList({}));
        domain = [
            "|",
            ["role_id", "=", false],
            "&",
            ["resource_id", "!=", false],
            ["start_datetime", "=", false],
            ["sale_line_id", "!=", false],
        ];
        newDomain = Domain.removeDomainLeaves(domain, keysToRemove);
        expectedDomain = new Domain([
            "|",
            ["role_id", "=", false],
            "&",
            ["resource_id", "!=", false],
            ...Domain.TRUE.toList({}),
            ["sale_line_id", "!=", false],
        ]);
        expect(newDomain.toList({})).toEqual(expectedDomain.toList({}));
        domain = [
            "|",
            ["start_datetime", "=", false],
            ["end_datetime", "=", false],
            ["sale_line_id", "!=", false],
        ];
        newDomain = Domain.removeDomainLeaves(domain, keysToRemove);
        expectedDomain = new Domain([...Domain.TRUE.toList({}), ["sale_line_id", "!=", false]]);
        expect(newDomain.toList({})).toEqual(expectedDomain.toList({}));
    });
});
