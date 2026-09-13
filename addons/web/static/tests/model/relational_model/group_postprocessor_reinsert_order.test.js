// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { getGroupKey } from "@web/model/relational_model/group_key";
import { postprocessReadGroup } from "@web/model/relational_model/group_postprocessor";

function makeConfig() {
    return /** @type {any} */ ({
        resModel: "task",
        fields: { name: { type: "char", name: "name" } },
        activeFields: {},
        fieldsToAggregate: [],
        domain: [],
        groupBy: ["name"],
        offset: 0,
        limit: 80,
        orderBy: [],
        groups: {},
    });
}

const DEPS = {
    getPropertyDefinition: async () => {},
    groupByInfo: {},
    initialLimit: 40,
    initialGroupsLimit: 10,
    defaultGroupLimit: 10,
};

async function runPostprocess(/** @type {any} */ config, /** @type {any} */ names) {
    const response = {
        groups: names.map((/** @type {any} */ name) => ({
            __count: 1,
            __extra_domain: [["name", "=", name]],
            name,
        })),
        length: names.length,
    };
    return postprocessReadGroup(config, response, DEPS);
}

describe("sticky-empty re-insertion order", () => {
    test("a survivor between two dropped groups keeps the dropped ones apart", async () => {
        const config = makeConfig();
        await runPostprocess(config, ["A", "B", "C", "D"]);

        const { groups } = await runPostprocess(config, ["A", "C"]);

        expect(groups.map((g) => g.value)).toEqual(["A", "B", "C", "D"]);
    });

    test("several survivors interleaved with drops stay in order", async () => {
        const config = makeConfig();
        await runPostprocess(config, ["A", "B", "C", "D", "E", "F"]);

        const { groups } = await runPostprocess(config, ["B", "D", "F"]);

        expect(groups.map((g) => g.value)).toEqual(["A", "B", "C", "D", "E", "F"]);
    });
});

function makeRng(/** @type {number} */ seed) {
    let state = seed >>> 0;
    return () => {
        state = (state * 1664525 + 1013904223) >>> 0;
        return state / 0x100000000;
    };
}

describe("sticky-empty merge properties", () => {
    test("survivors keep server order and drops are restored in place", async () => {
        const rng = makeRng(20260731);
        for (let iteration = 0; iteration < 400; iteration++) {
            const size = 2 + Math.floor(rng() * 7);
            const initial = Array.from({ length: size }, (_, i) => `G${i}`);

            const config = makeConfig();
            await runPostprocess(config, initial);

            const survivors = initial.filter(() => rng() > 0.5);
            const { groups } = await runPostprocess(config, survivors);
            const merged = groups.map((g) => g.value);

            expect(merged).toEqual(initial, {
                message: `iteration ${iteration}: survivors=${JSON.stringify(survivors)}`,
            });
        }
    });

    test("a group dropped from config is not restored, the rest keep order", async () => {
        const rng = makeRng(7);
        for (let iteration = 0; iteration < 200; iteration++) {
            const size = 3 + Math.floor(rng() * 6);
            const initial = Array.from({ length: size }, (_, i) => `G${i}`);

            const config = makeConfig();
            await runPostprocess(config, initial);

            const survivors = initial.filter(() => rng() > 0.5);
            const forgettable = initial.filter((n) => !survivors.includes(n));
            const forgotten = forgettable.length
                ? forgettable[Math.floor(rng() * forgettable.length)]
                : null;
            if (forgotten !== null) {
                delete config.groups[getGroupKey(forgotten)];
            }

            const { groups } = await runPostprocess(config, survivors);
            const merged = groups.map((g) => g.value);

            const expected = initial.filter((n) => n !== forgotten);
            expect(merged).toEqual(expected, {
                message: `iteration ${iteration}: survivors=${JSON.stringify(survivors)} forgotten=${forgotten}`,
            });
            expect(new Set(merged).size).toBe(merged.length);
        }
    });
});
