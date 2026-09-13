// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { makeLogger } from "@web/core/debug/debug_logger";

const auditLog = makeLogger("web.search.audit");
import { user } from "@web/core/user";
import {
    getIrFilterDescription,
    irFilterToFavorite,
    reconciliateFavorites,
} from "@web/search/search_favorites";
import {
    FAVORITE_PRIVATE_GROUP,
    FAVORITE_SHARED_GROUP,
} from "@web/search/search_state";

describe.current.tags("headless");

function makeIrFilter(overrides = {}) {
    return {
        id: 7,
        name: "My favorite",
        user_ids: [2],
        context: "{}",
        domain: "[('foo', '=', 1)]",
        sort: '["foo", "bar desc"]',
        is_default: false,
        ...overrides,
    };
}

describe("irFilterToFavorite", () => {
    test("converts a valid ir.filter", () => {
        const favorite = irFilterToFavorite(makeIrFilter({ is_default: true }));

        expect(favorite.isInvalid).toBe(false);
        expect(favorite.description).toBe("My favorite");
        expect(favorite.serverSideId).toBe(7);
        expect(favorite.groupNumber).toBe(FAVORITE_PRIVATE_GROUP);
        expect(favorite.isDefault).toBe(true);
        expect(favorite.orderBy).toEqual([
            { asc: true, name: "foo" },
            { asc: false, name: "bar" },
        ]);
    });

    test("supports the '-field' orderBy notation and shared group number", () => {
        const favorite = irFilterToFavorite(
            makeIrFilter({ user_ids: [], sort: '["-foo"]' }),
        );

        expect(favorite.groupNumber).toBe(FAVORITE_SHARED_GROUP);
        expect(favorite.orderBy).toEqual([{ asc: false, name: "foo" }]);
    });

    test("drops blank sort entries instead of emitting a nameless order term", () => {
        const favorite = irFilterToFavorite(
            makeIrFilter({ sort: '["name", "", "   ", "-bar"]' }),
        );

        expect(favorite.orderBy).toEqual([
            { asc: true, name: "name" },
            { asc: false, name: "bar" },
        ]);
        expect(favorite.isInvalid).toBe(true);
    });

    test("a lone minus sign is a blank field name, not a descending sort", () => {
        const favorite = irFilterToFavorite(makeIrFilter({ sort: '["-"]' }));

        expect(favorite.orderBy).toEqual([]);
        expect(favorite.isInvalid).toBe(true);
    });

    test("parses SQL direction case-insensitively and tolerates extra spaces", () => {
        const favorite = irFilterToFavorite(
            makeIrFilter({ sort: '["name ASC", "bar  DESC", "baz"]' }),
        );

        expect(favorite.orderBy).toEqual([
            { asc: true, name: "name" },
            { asc: false, name: "bar" },
            { asc: true, name: "baz" },
        ]);
    });

    test("extracts group_by from the context", () => {
        const favorite = irFilterToFavorite(
            makeIrFilter({ context: "{'group_by': ['stage_id'], 'keep': 1}" }),
        );

        expect(favorite.groupBys).toEqual(["stage_id"]);
        expect(favorite.context).toEqual({ keep: 1 });
    });

    test("quarantines an unparseable context", () => {
        const favorite = irFilterToFavorite(makeIrFilter({ context: "{'invalid" }));

        expect(favorite.isInvalid).toBe(true);
        expect(favorite.context).toEqual({});
    });

    test("quarantines an unparseable domain", () => {
        const favorite = irFilterToFavorite(makeIrFilter({ domain: "[(" }));

        expect(favorite.isInvalid).toBe(true);
    });

    test("quarantines a non-array sort blob instead of crashing", () => {
        const favorite = irFilterToFavorite(makeIrFilter({ sort: "false" }));

        expect(favorite.isInvalid).toBe(true);
        expect(favorite.orderBy).toEqual([]);
    });

    test("quarantines a sort array with non-string elements instead of crashing", () => {
        for (const sort of ["[null]", "[123]", '["ok", null]']) {
            const favorite = irFilterToFavorite(makeIrFilter({ sort }));
            expect(favorite.isInvalid).toBe(true);
            expect(favorite.orderBy).toEqual([]);
        }
    });

    test("a quarantined favorite never becomes the default", () => {
        const favorite = irFilterToFavorite(
            makeIrFilter({ sort: "false", is_default: true }),
        );

        auditLog.logic("favorite-context", () => ({
            context: favorite.context,
            invalid: favorite.isInvalid,
        }));
        expect(favorite.isDefault).toBe(undefined);
    });

    test("screens out group_by entries naming unknown fields (with warning)", () => {
        const fields = {
            name: { type: "char" },
            date_field: { type: "date" },
            props: { type: "properties" },
        };
        const warnings = [];
        const originalWarn = console.warn;
        console.warn = (...args) => warnings.push(args.join(" "));
        let favorite;
        try {
            favorite = irFilterToFavorite(
                makeIrFilter({
                    context:
                        "{'group_by': ['ghost_field', 'name', 'date_field:month', 'props.subkey', 'gone.subkey']}",
                }),
                fields,
            );
        } finally {
            console.warn = originalWarn;
        }
        expect(warnings.length).toBe(2);
        expect(warnings[0]).toInclude("ghost_field");
        expect(warnings[1]).toInclude("gone.subkey");

        expect(favorite.groupBys).toEqual(["name", "date_field:month", "props.subkey"]);
        expect(favorite.isInvalid).toBe(false);
    });

    test("without field metadata, group_bys are imported unscreened", () => {
        const favorite = irFilterToFavorite(
            makeIrFilter({ context: "{'group_by': ['ghost_field']}" }),
        );

        expect(favorite.groupBys).toEqual(["ghost_field"]);
    });
});

describe("getIrFilterDescription", () => {
    function makeParams(overrides = {}) {
        return {
            description: "Sales this year",
            isDefault: true,
            isShared: true,
            localContext: {},
            getContext: () => ({ custom_key: 1, search_default_x: 1 }),
            getDomain: () => ({ toString: () => "[('x', '=', 1)]" }),
            getGroupBy: () => ["stage_id", "date:month"],
            getOrderBy: () => [
                { name: "foo", asc: true },
                { name: "bar", asc: false },
            ],
            globalContext: {},
            actionId: 55,
            resModel: "res.partner",
            ...overrides,
        };
    }

    test("serializes orderBy in 'field desc' notation and strips defaults", () => {
        const { irFilter } = getIrFilterDescription(makeParams());

        expect(irFilter.sort).toBe('["foo","bar desc"]');
        expect(irFilter.context.group_by).toEqual(["stage_id", "date:month"]);
        expect(irFilter.context.custom_key).toBe(1);
        expect("search_default_x" in irFilter.context).toBe(false);
        expect(irFilter.user_ids).toEqual([]);
        expect(irFilter.is_default).toBe(true);
    });

    test("keeps intentional overrides of user-context keys, strips seeded values", () => {
        const userCtx = user.context;
        const overriddenLang = userCtx.lang === "fr_FR" ? "nl_NL" : "fr_FR";
        const { irFilter, preFavorite } = getIrFilterDescription(
            makeParams({
                getContext: () => ({
                    ...userCtx,
                    lang: overriddenLang,
                    custom_key: 1,
                }),
            }),
        );

        expect(irFilter.context.lang).toBe(overriddenLang);
        expect(preFavorite.context.lang).toBe(overriddenLang);
        expect(irFilter.context.custom_key).toBe(1);
        expect("tz" in irFilter.context).toBe(false);
        expect("uid" in irFilter.context).toBe(false);
    });

    test("strips a user-context key whose value is a shared array", () => {
        const userCtx = user.context;
        expect(Array.isArray(userCtx.allowed_company_ids)).toBe(true);

        const { irFilter, preFavorite } = getIrFilterDescription(
            makeParams({
                getContext: () => ({ ...userCtx, custom_key: 1 }),
            }),
        );

        expect("allowed_company_ids" in irFilter.context).toBe(false);
        expect("allowed_company_ids" in preFavorite.context).toBe(false);
        expect(irFilter.context.custom_key).toBe(1);
    });

    test("round-trips through irFilterToFavorite", () => {
        const { irFilter } = getIrFilterDescription(makeParams());

        const favorite = irFilterToFavorite({
            ...irFilter,
            id: 1,
            context: JSON.stringify(irFilter.context),
        });

        expect(favorite.isInvalid).toBe(false);
        expect(favorite.description).toBe("Sales this year");
        expect(favorite.groupBys).toEqual(["stage_id", "date:month"]);
        expect(favorite.orderBy).toEqual([
            { asc: true, name: "foo" },
            { asc: false, name: "bar" },
        ]);
        expect(favorite.domain).toBe("[('x', '=', 1)]");
        expect(favorite.isDefault).toBe(true);
        expect(favorite.groupNumber).toBe(FAVORITE_SHARED_GROUP);
    });
});

describe("reconciliateFavorites", () => {
    test("replaces a changed favorite instead of merging stale keys", () => {
        const searchItems = {
            3: {
                id: 3,
                groupId: 9,
                type: "favorite",
                serverSideId: 7,
                isDefault: true,
                description: "Old name",
            },
        };
        const query = [{ searchItemId: 3 }];

        reconciliateFavorites(
            searchItems,
            query,
            [makeIrFilter({ is_default: false, name: "New name" })],
            irFilterToFavorite,
            () => {},
        );

        expect(searchItems[3].id).toBe(3);
        expect(searchItems[3].groupId).toBe(9);
        expect(searchItems[3].description).toBe("New name");
        expect("isDefault" in searchItems[3]).toBe(false);
        expect(query).toEqual([{ searchItemId: 3 }]);
    });

    test("deactivates an active favorite that reloads as invalid", () => {
        const searchItems = {
            3: { id: 3, groupId: 9, type: "favorite", serverSideId: 7 },
        };
        const query = [{ searchItemId: 3 }];

        reconciliateFavorites(
            searchItems,
            query,
            [makeIrFilter({ domain: "[('foo', '=', " })],
            irFilterToFavorite,
            () => {},
        );

        expect(searchItems[3].isInvalid).toBe(true);
        expect(query).toEqual([]);
    });

    test("removes favorites deleted server-side, along with their query entries", () => {
        const searchItems = {
            3: { id: 3, groupId: 9, type: "favorite", serverSideId: 7 },
        };
        const query = [{ searchItemId: 3 }];

        reconciliateFavorites(searchItems, query, [], irFilterToFavorite, () => {});

        expect(3 in searchItems).toBe(false);
        expect(query).toEqual([]);
    });

    test("creates favorites that only exist server-side", () => {
        const created = [];
        reconciliateFavorites(
            {},
            [],
            [makeIrFilter()],
            irFilterToFavorite,
            (irFilters) => created.push(...irFilters),
        );

        expect(created.length).toBe(1);
        expect(created[0].id).toBe(7);
    });
});

for (const context of ["None", "False", "7", "'text'", "[]", "{'group_by': [7]}"]) {
    test(`quarantines a structurally invalid favorite context: ${context}`, () => {
        const favorite = irFilterToFavorite(
            makeIrFilter({ context, is_default: true }),
        );
        expect(favorite.isInvalid).toBe(true);
        auditLog.logic("favorite-context", () => ({
            context: favorite.context,
            invalid: favorite.isInvalid,
        }));
        expect(favorite.isDefault).toBe(undefined);
        expect(favorite.context).toEqual({});
        expect(favorite.groupBys).toEqual([]);
    });
}

for (const groupBy of ["False", "None", "[]", "'foo'", "['foo']"]) {
    test(`favorite context preserves supported group-by value ${groupBy}`, () => {
        const favorite = irFilterToFavorite(
            makeIrFilter({
                context: `{'group_by': ${groupBy}, 'keep': 42}`,
                is_default: true,
            }),
        );
        auditLog.logic("valid-favorite-counterexample", () => ({ groupBy, favorite }));
        expect(favorite.isInvalid).toBe(false);
        expect(favorite.isDefault).toBe(true);
        expect(favorite.context.keep).toBe(42);
    });
}
