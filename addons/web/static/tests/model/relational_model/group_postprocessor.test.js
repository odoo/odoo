// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { makeTestRelationalModel } from "@web/../tests/model/relational_model/model_test_helpers";
import { makeLogger } from "@web/core/debug/debug_logger";
import { computeNextConfig } from "@web/model/relational_model/config_transitions";
import { DynamicGroupList } from "@web/model/relational_model/dynamic_group_list";
import { getGroupKey } from "@web/model/relational_model/group_key";
import { postprocessReadGroup } from "@web/model/relational_model/group_postprocessor";
import { getWebReadGroupParams } from "@web/model/relational_model/read_group_builder";

/** @returns {import("@web/model/relational_model/relational_model").RelationalModelConfig} */
function makeConfig() {
    return {
        resModel: "task",
        isMonoRecord: false,
        isRoot: true,
        context: {},
        fields: { name: { type: "char", name: "name" } },
        activeFields: {},
        fieldsToAggregate: [],
        domain: [],
        groupBy: ["name"],
        offset: 0,
        limit: 80,
        orderBy: [],
        groups: {},
    };
}

const DEPS = {
    getPropertyDefinition: async () => {},
    groupByInfo: {},
    initialLimit: 40,
    initialGroupsLimit: 10,
    defaultGroupLimit: 10,
};

test("an unset selection group stays distinct from a literal false selection on reload", async () => {
    const model = await makeTestRelationalModel({});
    const config = makeConfig();
    config.fields.name = {
        name: "name",
        type: "selection",
        selection: [["false", "Literal false"]],
    };
    const response = {
        length: 2,
        groups: [false, "false"].map((name, index) => ({
            ...makeGroupData(name),
            __records: [{ id: index + 1 }],
        })),
    };
    const first = new DynamicGroupList(
        model,
        config,
        await postprocessReadGroup(config, response, DEPS),
    );
    const next = computeNextConfig(config, {}, { hasRoot: true });
    const second = new DynamicGroupList(
        model,
        next,
        await postprocessReadGroup(next, response, DEPS),
        { previousRoot: first },
    );
    makeLogger("web.model.audit").logic("typed selection group identities", {
        keys: Object.keys(next.groups),
        domains: second.groups.map((g) => g.list.domain),
    });
    expect(second.groups.map((g) => g.value)).toEqual([false, "false"]);
    expect(second.groups[0].config).not.toBe(second.groups[1].config);
    expect(
        getWebReadGroupParams(next, DEPS).params.opening_info.map(
            (group) => group.value,
        ),
    ).toEqual([false, "false"]);
    for (let i = 0; i < 2; i++) {
        expect(second.groups[i].list.context.default_name).toBe(i ? "false" : false);
        expect(second.groups[i].list.records[0]).toBe(first.groups[i].list.records[0]);
    }
});

function makeGroupData(name, count = 1) {
    return {
        __count: count,
        __extra_domain: [["name", "=", name]],
        name,
    };
}

async function runPostprocess(config, names) {
    const response = {
        groups: names.map((name) => makeGroupData(name)),
        length: names.length,
    };
    return postprocessReadGroup(config, response, DEPS);
}

describe("sticky-empty group re-insertion", () => {
    test("dropped groups are re-inserted in order on an identical reload", async () => {
        const config = makeConfig();
        await runPostprocess(config, ["A", "B", "C", "D"]);

        const { groups } = await runPostprocess(config, ["D"]);

        expect(groups.map((g) => g.value)).toEqual(["A", "B", "C", "D"]);
        const emptied = groups.filter((g) => g.value !== "D");
        for (const group of emptied) {
            expect(group.count).toBe(0);
            expect(group.records).toEqual([]);
        }
    });

    test("re-insertion follows the merged array when survivors are reordered", async () => {
        const config = makeConfig();
        await runPostprocess(config, ["A", "B", "C"]);

        const { groups } = await runPostprocess(config, ["C", "A"]);

        expect(groups.map((g) => g.value)).toEqual(["C", "A", "B"]);
    });

    test("re-insertion is stable when a new group appears first", async () => {
        const config = makeConfig();
        await runPostprocess(config, ["A", "B"]);

        const { groups } = await runPostprocess(config, ["E", "A"]);

        expect(groups.map((g) => g.value)).toEqual(["E", "A", "B"]);
    });

    test("a changed query starts clean (no sticky re-insertion)", async () => {
        const config = makeConfig();
        await runPostprocess(config, ["A", "B"]);

        config.domain = [["name", "!=", false]];
        const { groups } = await runPostprocess(config, ["B"]);

        expect(groups.map((g) => g.value)).toEqual(["B"]);
    });

    test("a re-inserted group resets its nested subgroups (2-level grouping)", async () => {
        /** @type {import("@web/model/relational_model/relational_model").RelationalModelConfig} */
        const config = {
            ...makeConfig(),
            fields: {
                bar: { type: "char", name: "bar" },
                name: { type: "char", name: "name" },
            },
            groupBy: ["bar", "name"],
        };
        const makeNestedGroupData = (bar, subNames) => ({
            __count: subNames.length,
            __extra_domain: [["bar", "=", bar]],
            bar,
            __groups: {
                groups: subNames.map((name) => ({
                    __count: 1,
                    __extra_domain: [["name", "=", name]],
                    name,
                    __records: [{ id: subNames.indexOf(name) + 1, name }],
                })),
                length: subNames.length,
            },
        });
        const run = (names) =>
            postprocessReadGroup(
                config,
                {
                    groups: names.map((name) => makeNestedGroupData(name, ["x", "y"])),
                    length: names.length,
                },
                DEPS,
            );
        await run(["A", "B"]);

        const { groups } = await run(["B"]);

        expect(groups.map((g) => g.value)).toEqual(["A", "B"]);
        const sticky = groups[0];
        expect(sticky.count).toBe(0);
        expect(sticky.length).toBe(0);
        expect(sticky.groups).toEqual([]);
        expect(groups[1].groups.map((g) => g.value)).toEqual(["x", "y"]);
    });
});

for (const name of ["constructor", "toString", "__proto__"]) {
    test(`group value ${name} survives loading and config cloning as an own key`, async () => {
        const config = makeConfig();
        const { groups } = await runPostprocess(config, [name]);
        expect(groups.map((g) => g.value)).toEqual([name]);
        expect(Object.hasOwn(config.groups, getGroupKey(name))).toBe(true);
        const next = computeNextConfig(config, {}, { hasRoot: true });
        expect(Object.hasOwn(next.groups, getGroupKey(name))).toBe(true);
        expect(next.groups[getGroupKey(name)]).not.toBe(
            config.groups[getGroupKey(name)],
        );
        const reloaded = await runPostprocess(next, [name]);
        expect(reloaded.groups.map((g) => g.value)).toEqual([name]);
        expect(Object.getPrototypeOf(config.groups)).toBe(Object.prototype);
    });
}

test("prototype-like keys remain separate in real nested group datapoints after reload", async () => {
    const model = await makeTestRelationalModel({});
    const config = {
        ...makeConfig(),
        fields: {
            name: { name: "name", type: "char" },
            child: { name: "child", type: "char" },
        },
        groupBy: ["name", "child"],
    };
    const names = ["constructor", "toString", "__proto__"];
    const response = {
        length: 3,
        groups: names.map((name, index) => ({
            ...makeGroupData(name),
            __groups: {
                length: 1,
                groups: [
                    {
                        __count: 1,
                        __extra_domain: [["child", "=", name]],
                        child: name,
                        __records: [{ id: index + 1 }],
                    },
                ],
            },
        })),
    };
    const first = new DynamicGroupList(
        model,
        config,
        await postprocessReadGroup(config, response, DEPS),
    );
    const next = computeNextConfig(config, {}, { hasRoot: true });
    const second = new DynamicGroupList(
        model,
        next,
        await postprocessReadGroup(next, response, DEPS),
        { previousRoot: first },
    );
    const ids = second.groups.map((g) => g.list.groups[0].list.records[0].resId);
    makeLogger("web.model.audit").logic("nested prototype group reload", {
        names,
        ids,
    });
    expect(ids).toEqual([1, 2, 3]);
    for (let i = 0; i < names.length; i++) {
        expect(second.groups[i].value).toBe(names[i]);
        expect(second.groups[i].list.groups[0].value).toBe(names[i]);
        expect(second.groups[i].list.groups[0].list.records[0]).toBe(
            first.groups[i].list.groups[0].list.records[0],
        );
        expect(
            next.groups[getGroupKey(names[i])].list.groups[getGroupKey(names[i])],
        ).not.toBe(
            config.groups[getGroupKey(names[i])].list.groups[getGroupKey(names[i])],
        );
    }
});
