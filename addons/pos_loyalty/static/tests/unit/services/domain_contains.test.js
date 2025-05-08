import { describe, expect, test } from "@odoo/hoot";

import { Domain } from "@web/core/domain";
import { contains } from "@web/../tests/_framework/domain_contains";

describe.current.tags("headless");

const doesContain = (domain, record) => expect(contains(domain, record)).toBe(true);
const doesNotContain = (domain, record) => expect(contains(domain, record)).toBe(false);

test("empty", () => {
    doesContain([], {});
});

test("undefined domain", () => {
    doesContain(undefined, {});
});
test("simple condition", () => {
    doesContain([["a", "=", 3]], { a: 3 });
    doesNotContain([["a", "=", 3]], { a: 5 });
});

test("basic", () => {
    const record = {
        a: 3,
        group_method: "line",
        select1: "day",
        rrule_type: "monthly",
    };
    doesContain([["a", "=", 3]], record);
    doesNotContain([["a", "=", 5]], record);
    doesContain([["group_method", "!=", "count"]], record);
    doesContain(
        [
            ["select1", "=", "day"],
            ["rrule_type", "=", "monthly"],
        ],
        record
    );
});

test("support of '=?' operator", () => {
    const record = { a: 3 };
    doesContain([["a", "=?", null]], record);
    doesContain([["a", "=?", false]], record);
    doesNotContain(["!", ["a", "=?", false]], record);
    doesNotContain([["a", "=?", 1]], record);
    doesContain([["a", "=?", 3]], record);
    doesNotContain(["!", ["a", "=?", 3]], record);
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
    doesContain(currentDomain, { ...record, section_id: 42 });
    doesContain(currentDomain, { ...record, user_id: 3 });
    doesContain(currentDomain, { ...record, member_ids: 3 });
});

test("and", () => {
    const domain = ["&", "&", ["a", "=", 1], ["b", "=", 2], ["c", "=", 3]];
    doesContain(domain, { a: 1, b: 2, c: 3 });
    doesNotContain(domain, { a: -1, b: 2, c: 3 });
    doesNotContain(domain, { a: 1, b: -1, c: 3 });
    doesNotContain(domain, { a: 1, b: 2, c: -1 });
});

test("not", () => {
    const record = { a: 5, group_method: "line" };
    doesContain(["!", ["a", "=", 3]], record);
    doesContain(["!", ["group_method", "=", "count"]], record);
});

test("like, =like, ilike, =ilike and not likes", () => {
    doesContain([["a", "like", "value"]], { a: "value" });
    doesContain([["a", "like", "value"]], { a: "some value" });
    doesNotContain([["a", "like", "value"]], { a: "Some Value" });
    doesNotContain([["a", "like", "value"]], { a: false });

    doesContain([["a", "=like", "%value"]], { a: "value" });
    doesContain([["a", "=like", "%value"]], { a: "some value" });
    doesNotContain([["a", "=like", "%value"]], { a: "Some Value" });
    doesNotContain([["a", "=like", "%value"]], { a: false });

    doesContain([["a", "ilike", "value"]], { a: "value" });
    doesContain([["a", "ilike", "value"]], { a: "some value" });
    doesContain([["a", "ilike", "value"]], { a: "Some Value" });
    doesNotContain([["a", "ilike", "value"]], { a: false });

    doesContain([["a", "=ilike", "%value"]], { a: "value" });
    doesContain([["a", "=ilike", "%value"]], { a: "some value" });
    doesContain([["a", "=ilike", "%value"]], { a: "Some Value" });
    doesNotContain([["a", "=ilike", "%value"]], { a: false });

    doesNotContain([["a", "not like", "value"]], { a: "value" });
    doesNotContain([["a", "not like", "value"]], { a: "some value" });
    doesContain([["a", "not like", "value"]], { a: "Some Value" });
    doesContain([["a", "not like", "value"]], { a: "something" });
    doesContain([["a", "not like", "value"]], { a: "Something" });
    doesContain([["a", "not like", "value"]], { a: false });

    doesNotContain([["a", "not ilike", "value"]], { a: "value" });
    doesNotContain([["a", "not ilike", "value"]], { a: "some value" });
    doesNotContain([["a", "not ilike", "value"]], { a: "Some Value" });
    doesContain([["a", "not ilike", "value"]], { a: "something" });
    doesContain([["a", "not ilike", "value"]], { a: "Something" });
    doesContain([["a", "not ilike", "value"]], { a: false });

    doesNotContain([["a", "not =like", "%value"]], { a: "some value" });
    doesContain([["a", "not =like", "%value"]], { a: "Some Value" });

    doesNotContain([["a", "not =ilike", "%value"]], { a: "value" });
    doesNotContain([["a", "not =ilike", "%value"]], { a: "some value" });
    doesNotContain([["a", "not =ilike", "%value"]], { a: "Some Value" });
    doesContain([["a", "not =ilike", "%value"]], { a: false });
});

test("complex domain", () => {
    const domain = ["&", "!", ["a", "=", 1], "|", ["a", "=", 2], ["a", "=", 3]];
    doesNotContain(domain, { a: 1 });
    doesContain(domain, { a: 2 });
    doesContain(domain, { a: 3 });
    doesNotContain(domain, { a: 4 });
});

test("implicit &", () => {
    const domain = [
        ["a", "=", 3],
        ["b", "=", 4],
    ];
    doesNotContain(domain, {});
    doesContain(domain, { a: 3, b: 4 });
    doesNotContain(domain, { a: 3, b: 5 });
});

test("comparison operators", () => {
    doesContain([["a", "=", 3]], { a: 3 });
    doesNotContain([["a", "=", 3]], { a: 4 });
    doesContain([["a", "==", 3]], { a: 3 });
    doesNotContain([["a", "==", 3]], { a: 4 });
    doesNotContain([["a", "!=", 3]], { a: 3 });
    doesContain([["a", "!=", 3]], { a: 4 });
    doesNotContain([["a", "<>", 3]], { a: 3 });
    doesContain([["a", "<>", 3]], { a: 4 });
    doesNotContain([["a", "<", 3]], { a: 5 });
    doesNotContain([["a", "<", 3]], { a: 3 });
    doesContain([["a", "<", 3]], { a: 2 });
    doesNotContain([["a", "<=", 3]], { a: 5 });
    doesContain([["a", "<=", 3]], { a: 3 });
    doesContain([["a", "<=", 3]], { a: 2 });
    doesContain([["a", ">", 3]], { a: 5 });
    doesNotContain([["a", ">", 3]], { a: 3 });
    doesNotContain([["a", ">", 3]], { a: 2 });
    doesContain([["a", ">=", 3]], { a: 5 });
    doesContain([["a", ">=", 3]], { a: 3 });
    doesNotContain([["a", ">=", 3]], { a: 2 });
});

test("other operators", () => {
    doesContain([["a", "in", 3]], { a: 3 });
    doesContain([["a", "in", [1, 2, 3]]], { a: 3 });
    doesContain([["a", "in", [1, 2, 3]]], { a: [3] });
    doesNotContain([["a", "in", 3]], { a: 5 });
    doesNotContain([["a", "in", [1, 2, 3]]], { a: 5 });
    doesNotContain([["a", "in", [1, 2, 3]]], { a: [5] });
    doesNotContain([["a", "not in", 3]], { a: 3 });
    doesNotContain([["a", "not in", [1, 2, 3]]], { a: 3 });
    doesNotContain([["a", "not in", [1, 2, 3]]], { a: [3] });
    doesContain([["a", "not in", 3]], { a: 5 });
    doesContain([["a", "not in", [1, 2, 3]]], { a: 5 });
    doesContain([["a", "not in", [1, 2, 3]]], { a: [5] });
    doesContain([["a", "like", "abc"]], { a: "abc" });
    doesNotContain([["a", "like", "abc"]], { a: "def" });
    doesContain([["a", "=like", "abc"]], { a: "abc" });
    doesNotContain([["a", "=like", "abc"]], { a: "def" });
    doesContain([["a", "ilike", "abc"]], { a: "abc" });
    doesNotContain([["a", "ilike", "abc"]], { a: "def" });
    doesContain([["a", "=ilike", "abc"]], { a: "abc" });
    doesNotContain([["a", "=ilike", "abc"]], { a: "def" });
});

test("TRUE and FALSE Domain", () => {
    doesContain(Domain.TRUE, {});
    doesNotContain(Domain.FALSE, {});
    doesContain(Domain.and([Domain.TRUE, new Domain([["a", "=", 3]])]), { a: 3 });
    doesNotContain(Domain.and([Domain.FALSE, new Domain([["a", "=", 3]])]), { a: 3 });
});
test("follow relations", () => {
    doesContain([["partner.city", "ilike", "Bru"]], {
        name: "Lucas",
        partner: {
            city: "Bruxelles",
        },
    });
    doesContain([["partner.city.name", "ilike", "Bru"]], {
        name: "Lucas",
        partner: {
            city: {
                name: "Bruxelles",
            },
        },
    });
});

test("Arrays comparison", () => {
    const domain = new Domain(["&", ["a", "==", []], ["b", "!=", []]]);
    doesContain(domain, { a: [] });
    doesContain(domain, { a: [], b: [4] });
    doesNotContain(domain, { a: [1] });
    doesNotContain(domain, { b: [] });
});

test("combining zero domain", () => {
    doesContain(Domain.combine([], "AND"), { a: 1, b: 2 });
});
