// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { markup } from "@odoo/owl";
import { MODEL_LIFECYCLE_PROTO } from "@web/../tests/model/relational_model/model_doubles";
import { makeTestRelationalModel } from "@web/../tests/model/relational_model/model_test_helpers";
import { makeLogger } from "@web/core/debug/debug_logger";
import { x2ManyCommands } from "@web/core/network/commands";
import { makeActiveField } from "@web/model/relational_model/field_metadata";
import {
    completeMany2OneValue,
    preprocessHtmlChanges,
    preprocessMany2oneChanges,
    preprocessMany2OneReferenceChanges,
    preprocessPropertiesChanges,
    preprocessReferenceChanges,
    preprocessX2manyChanges,
} from "@web/model/relational_model/record_preprocessors";

/**
 * @param {Object} [opts]
 * @param {Object} [opts.fields]
 * @param {Object} [opts.activeFields]
 * @param {Object} [opts.data]
 * @param {Function} [opts.ormCall]
 * @param {Function} [opts.ormWebRead]
 * @param {Function} [opts.processProperties]
 * @param {Function} [opts.onDisplayPropertyWarning]
 * @returns {Object}
 */
function makeRecord({
    fields = {},
    activeFields = {},
    data = {},
    ormCall = async () => null,
    ormWebRead = async () => [],
    processProperties = () => ({}),
    onDisplayPropertyWarning = () => {},
} = {}) {
    return {
        context: {},
        evalContext: {},
        config: { context: { uid: 1, allowed_company_ids: [1] } },
        fields,
        activeFields,
        data,
        model: {
            orm: { call: ormCall, webRead: ormWebRead },
            __proto__: MODEL_LIFECYCLE_PROTO,
            hooks: { lifecycle: {}, ui: { onDisplayPropertyWarning } },
        },
        processProperties: processProperties,
    };
}

describe("completeMany2OneValue", () => {
    test("returns false when value has no id and no display_name", async () => {
        const rec = makeRecord({
            fields: { partner_id: { type: "many2one", context: {} } },
            activeFields: { partner_id: { context: "{}" } },
        });
        const result = await completeMany2OneValue(
            rec,
            {},
            "partner_id",
            "res.partner",
        );
        expect(result).toBe(false);
    });

    test("calls name_create when display_name is present but id is absent", async () => {
        /** @type {{ model: string, method: string, args: unknown[] }} */
        let nameCreateArgs;
        const rec = makeRecord({
            fields: { partner_id: { type: "many2one", context: {} } },
            activeFields: { partner_id: { context: "{}", related: null } },
            ormCall: async (model, method, args) => {
                nameCreateArgs = { model, method, args };
                return [42, "Acme Corp"];
            },
        });
        const result = await completeMany2OneValue(
            rec,
            { display_name: "Acme Corp" },
            "partner_id",
            "res.partner",
        );
        expect(nameCreateArgs.method).toBe("name_create");
        expect(nameCreateArgs.args).toEqual(["Acme Corp"]);
        expect(result).toEqual({ id: 42, display_name: "Acme Corp" });
    });

    test("calls webRead when id is present but display_name is undefined", async () => {
        /** @type {{ model: string, ids: number[] }} */
        let webReadArgs;
        const rec = makeRecord({
            fields: { partner_id: { type: "many2one", context: {} } },
            activeFields: { partner_id: { context: "{}", related: null } },
            ormWebRead: async (model, ids) => {
                webReadArgs = { model, ids };
                return [{ id: 42, display_name: "Acme Corp" }];
            },
        });
        const result = await completeMany2OneValue(
            rec,
            { id: 42 },
            "partner_id",
            "res.partner",
        );
        expect(webReadArgs.ids).toEqual([42]);
        expect(result).toEqual({ id: 42, display_name: "Acme Corp" });
    });

    test("returns value as-is when both id and display_name are provided", async () => {
        const rec = makeRecord({
            fields: { partner_id: { type: "many2one", context: {} } },
            activeFields: { partner_id: { context: "{}" } },
        });
        const value = { id: 42, display_name: "Acme Corp" };
        const result = await completeMany2OneValue(
            rec,
            value,
            "partner_id",
            "res.partner",
        );
        expect(result).toBe(value);
    });
});

describe("preprocessMany2oneChanges", () => {
    test("sets falsy many2one change to false", async () => {
        const rec = makeRecord({
            fields: { partner_id: { type: "many2one", context: {} } },
            activeFields: { partner_id: { context: "{}" } },
        });
        /** @type {{partner_id: number | false}} */
        const changes = { partner_id: 0 };
        await preprocessMany2oneChanges(rec, changes);
        expect(changes.partner_id).toBe(false);
    });

    test("keeps value unchanged when field is not in activeFields", async () => {
        const rec = makeRecord({
            fields: { partner_id: { type: "many2one", context: {} } },
            activeFields: {},
        });
        const original = { id: 1, display_name: "kept" };
        const changes = { partner_id: original };
        await preprocessMany2oneChanges(rec, changes);
        expect(changes.partner_id).toBe(original);
    });

    test("completes value when field is in activeFields with both id and display_name", async () => {
        const rec = makeRecord({
            fields: {
                partner_id: { type: "many2one", relation: "res.partner", context: {} },
            },
            activeFields: { partner_id: { context: "{}", related: null } },
        });
        const changes = { partner_id: { id: 5, display_name: "Acme" } };
        await preprocessMany2oneChanges(rec, changes);
        expect(changes.partner_id).toEqual({ id: 5, display_name: "Acme" });
    });
});

describe("preprocessMany2OneReferenceChanges", () => {
    test("sets falsy many2one_reference change to false", async () => {
        const rec = makeRecord({
            fields: { ref_id: { type: "many2one_reference", context: {} } },
            activeFields: { ref_id: { context: "{}" } },
        });
        const changes = { ref_id: null };
        await preprocessMany2OneReferenceChanges(rec, changes);
        expect(changes.ref_id).toBe(false);
    });

    test("wraps a numeric id into { resId } without an RPC call", async () => {
        let ormCalled = false;
        const rec = makeRecord({
            fields: { ref_id: { type: "many2one_reference", context: {} } },
            activeFields: {},
            ormCall: async () => {
                ormCalled = true;
                return null;
            },
        });
        /** @type {{ref_id: number | {resId: number}}} */
        const changes = { ref_id: 42 };
        await preprocessMany2OneReferenceChanges(rec, changes);
        expect(changes.ref_id).toEqual({ resId: 42 });
        expect(ormCalled).toBe(false);
    });
});

describe("preprocessReferenceChanges", () => {
    test("sets falsy reference change to false", async () => {
        const rec = makeRecord({
            fields: { ref_field: { type: "reference", context: {} } },
            activeFields: { ref_field: { context: "{}" } },
        });
        const changes = { ref_field: false };
        await preprocessReferenceChanges(rec, changes);
        expect(changes.ref_field).toBe(false);
    });

    test("normalises a reference object when both resId and displayName are provided", async () => {
        const rec = makeRecord({
            fields: { ref_field: { type: "reference", context: {} } },
            activeFields: { ref_field: { context: "{}", related: null } },
        });
        const changes = {
            ref_field: { resId: 5, displayName: "Acme", resModel: "res.partner" },
        };
        await preprocessReferenceChanges(rec, changes);
        expect(changes.ref_field).toEqual({
            resId: 5,
            resModel: "res.partner",
            displayName: "Acme",
        });
    });
});

describe("preprocessX2manyChanges", () => {
    test("SET command calls list.replaceWith with the new ids array", async () => {
        let replacedWith = null;
        const list = {
            replaceWith: async (ids) => {
                replacedWith = ids;
            },
            applyCommandsLocked: async () => {},
        };
        const rec = makeRecord({
            fields: { turtles: { type: "one2many" } },
            data: { turtles: list },
        });
        /** @type {{turtles: import("@web/core/network/commands").X2ManyCommand[] | typeof list}} */
        const changes = { turtles: [x2ManyCommands.set([1, 2, 3])] };
        await preprocessX2manyChanges(rec, changes);
        expect(replacedWith).toEqual([1, 2, 3]);
        expect(changes.turtles).toBe(list);
    });

    test("non-SET command calls list.applyCommandsLocked with a single-element array", async () => {
        let appliedCommands = null;
        const list = {
            replaceWith: async () => {},
            applyCommandsLocked: async (cmds) => {
                appliedCommands = cmds;
            },
        };
        const deleteCmd = x2ManyCommands.delete(7);
        const rec = makeRecord({
            fields: { turtles: { type: "one2many" } },
            data: { turtles: list },
        });
        /** @type {{turtles: import("@web/core/network/commands").X2ManyCommand[] | typeof list}} */
        const changes = { turtles: [deleteCmd] };
        await preprocessX2manyChanges(rec, changes);
        expect(appliedCommands).toEqual([deleteCmd]);
        expect(changes.turtles).toBe(list);
    });
});

describe("preprocessPropertiesChanges", () => {
    test("properties field calls processProperties and merges result into changes", () => {
        const rec = makeRecord({
            fields: {
                my_props: { type: "properties", definition_record: "project_id" },
            },
            data: { project_id: { id: 1 } },
            processProperties: () => ({ extra_key: "computed" }),
        });
        const changes = { my_props: [{ name: "color", value: "red" }] };
        preprocessPropertiesChanges(rec, changes);
        expect(changes.extra_key).toBe("computed");
    });

    test("relatedPropertyField maps updated value into the parent properties array", () => {
        const rec = makeRecord({
            fields: {
                "my_props.color": {
                    type: "char",
                    relatedPropertyField: true,
                    name: "my_props.color",
                },
            },
            data: {
                my_props: [{ name: "color", value: "red" }],
            },
        });
        const changes = { "my_props.color": "blue" };
        preprocessPropertiesChanges(rec, changes);
        expect(changes.my_props).toEqual([{ name: "color", value: "blue" }]);
    });

    test("relatedPropertyField calls onDisplayPropertyWarning when property not found", () => {
        let warned = false;
        const rec = makeRecord({
            fields: {
                "other.color": {
                    type: "char",
                    relatedPropertyField: true,
                    name: "other.color",
                },
            },
            data: {
                other: [{ name: "size", value: "large" }],
            },
            onDisplayPropertyWarning: () => {
                warned = true;
            },
        });
        const changes = { "other.color": "blue" };
        preprocessPropertiesChanges(rec, changes);
        expect(warned).toBe(true);
        expect(changes["other"]).toBe(undefined);
    });
});

describe("preprocessHtmlChanges", () => {
    test("wraps html field string value with markup()", () => {
        const rec = makeRecord({
            fields: { description: { type: "html" } },
        });
        /** @type {{description: string | import("@odoo/owl").Markup}} */
        const changes = { description: "<p>hello</p>" };
        preprocessHtmlChanges(rec, changes);
        expect(String(changes.description)).toBe("<p>hello</p>");
        expect(changes.description).not.toBe("<p>hello</p>");
        expect(changes.description).toEqual(markup("<p>hello</p>"));
    });

    test("passes false through without wrapping for html field", () => {
        const rec = makeRecord({
            fields: { description: { type: "html" } },
        });
        const changes = { description: false };
        preprocessHtmlChanges(rec, changes);
        expect(changes.description).toBe(false);
    });
});

test("updating two properties together preserves both values without mutating saved data", () => {
    const properties = [
        { name: "color", value: "red" },
        { name: "size", value: "small" },
    ];
    const rec = makeRecord({
        fields: Object.fromEntries(
            ["color", "size"].map((name) => [
                `my_props.${name}`,
                { name: `my_props.${name}`, type: "char", relatedPropertyField: true },
            ]),
        ),
        data: { my_props: properties },
    });
    const changes = { "my_props.color": "blue", "my_props.size": "large" };
    preprocessPropertiesChanges(rec, changes);
    expect(changes.my_props).toEqual([
        { name: "color", value: "blue" },
        { name: "size", value: "large" },
    ]);
    expect(properties).toEqual([
        { name: "color", value: "red" },
        { name: "size", value: "small" },
    ]);
});

for (const reverse of [false, true]) {
    test(`explicit property edits override an aggregate update, reverse=${reverse}`, () => {
        const fields = {
            props: {
                name: "props",
                type: "properties",
                definition_record: "parent_id",
            },
            "props.color": {
                name: "props.color",
                type: "char",
                relatedPropertyField: true,
            },
        };
        const rec = makeRecord({
            fields,
            processProperties: (props) => ({ "props.color": props[0].value }),
        });
        const entries = [
            ["props.color", "blue"],
            ["props", [{ name: "color", value: "red" }]],
        ];
        const changes = Object.fromEntries(reverse ? entries.reverse() : entries);
        preprocessPropertiesChanges(rec, changes);
        makeLogger("web.model.audit").logic(
            "aggregate and dotted property precedence",
            { reverse, changes },
        );
        expect(changes["props.color"]).toBe("blue");
        expect(changes.props).toEqual([{ name: "color", value: "blue" }]);
    });
    test(`property siblings serialize completed relations, reverse=${reverse}`, async () => {
        const model = await makeTestRelationalModel({
            loadRecords: async () => [
                {
                    id: 1,
                    props: [
                        {
                            name: "owner",
                            string: "Owner",
                            type: "many2one",
                            comodel: "res.partner",
                            value: [2, "Old"],
                        },
                        { name: "color", string: "Color", type: "char", value: "red" },
                        {
                            name: "watchers",
                            string: "Watchers",
                            type: "many2many",
                            comodel: "res.partner",
                            value: [
                                [2, "Old"],
                                [3, "Removed"],
                                [4, "Hidden"],
                            ],
                        },
                    ],
                },
            ],
        });
        model.patchConfig(model.config, {
            isMonoRecord: true,
            resId: 1,
            resIds: [1],
            mode: "edit",
            fields: {
                props: {
                    name: "props",
                    type: "properties",
                    definition_record: "parent_id",
                },
            },
            activeFields: { props: makeActiveField() },
        });
        await model.load();
        await model.root.data["props.watchers"].load({ limit: 1 });
        model.orm = {
            ...model.orm,
            call: async (_model, method) => {
                expect(method).toBe("name_create");
                return [42, "New"];
            },
        };
        const entries = [
            ["props.owner", { display_name: "New" }],
            ["props.color", "blue"],
            [
                "props.watchers",
                [
                    x2ManyCommands.unlink(3),
                    [x2ManyCommands.LINK, 5, { id: 5, display_name: "Added" }],
                ],
            ],
        ];
        await model.root.update(
            Object.fromEntries(reverse ? entries.reverse() : entries),
            { withoutOnchange: true },
        );
        const serialized = model.root.getChangesLocked();
        makeLogger("web.model.audit").logic("property sibling serialization", {
            reverse,
            serialized,
        });
        expect(model.root.data["props.owner"]).toEqual({ id: 42, display_name: "New" });
        expect(serialized.props.map((p) => [p.name, p.value])).toEqual([
            ["owner", [42, "New"]],
            ["color", "blue"],
            [
                "watchers",
                [
                    [2, "Old"],
                    [4, "Hidden"],
                    [5, "Added"],
                ],
            ],
        ]);
        expect(model.root.data["props.watchers"].records.length).toBe(1);
        await model.root.discard();
        expect(model.root.data["props.owner"]).toEqual({ id: 2, display_name: "Old" });
        expect(model.root.data["props.color"]).toBe("red");
        expect(model.root.data["props.watchers"].resIds).toEqual([2, 3, 4]);
        model.orm = {
            ...model.orm,
            call: async () => {
                throw new Error("creation rejected");
            },
        };
        let failure;
        try {
            await model.root.update(
                { "props.owner": { display_name: "Rejected" }, "props.color": "green" },
                { withoutOnchange: true },
            );
        } catch (error) {
            failure = error;
        }
        makeLogger("web.model.audit").logic("property completion rejection", {
            message: failure?.message,
            changes: model.root.getChangesLocked(),
        });
        expect(failure?.message).toBe("creation rejected");
        expect(model.root.getChangesLocked()).toEqual({});
        expect(model.root.data["props.color"]).toBe("red");

        const originalProcessProperties = model.root.processProperties;
        const originalOnUpdate = model.root._onUpdate;
        for (const failurePoint of ["relation", "properties", "parent"]) {
            const synchronous = failurePoint === "properties";
            model.root._onUpdate =
                failurePoint === "parent"
                    ? async () => {
                          throw new Error("parent rejected");
                      }
                    : originalOnUpdate;
            const pending = new Deferred();
            let loadStarted = false;
            model.loadRecords = async () => {
                loadStarted = true;
                return pending;
            };
            model.root.processProperties = synchronous
                ? () => {
                      throw new Error("properties rejected");
                  }
                : originalProcessProperties;
            let settled = false;
            const delayedId = failurePoint === "parent" ? 8 : synchronous ? 7 : 6;
            const update = {
                "props.watchers": [x2ManyCommands.set([2, delayedId])],
                ...(synchronous
                    ? { props: [] }
                    : failurePoint === "relation"
                      ? { "props.owner": { display_name: "Rejected" } }
                      : {}),
            };
            const updating = model.root.update(update, { withoutOnchange: true }).then(
                () => {
                    settled = true;
                },
                (error) => {
                    settled = true;
                    failure = error;
                },
            );
            await animationFrame();
            expect(loadStarted).toBe(true);
            makeLogger("web.model.audit").logic(
                "property preprocessing before delayed completion",
                { failurePoint, settled },
            );
            expect(settled).toBe(false);
            pending.resolve([{ id: delayedId, display_name: "Delayed" }]);
            await updating;
            await animationFrame();
            model.root.processProperties = originalProcessProperties;
            model.root._onUpdate = originalOnUpdate;
            makeLogger("web.model.audit").logic(
                "property preprocessing after rejection",
                {
                    failurePoint,
                    ids: [...model.root.data["props.watchers"].currentIds],
                    changes: model.root.getChangesLocked(),
                },
            );
            expect(failure?.message).toBe(
                failurePoint === "parent"
                    ? "parent rejected"
                    : synchronous
                      ? "properties rejected"
                      : "creation rejected",
            );
            expect(model.root.data["props.watchers"].currentIds).toEqual([2, 3, 4]);
            expect(model.root.getChangesLocked()).toEqual({});
        }
    });
}
