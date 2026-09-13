// @ts-check

import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    defineModels,
    defineWebModels,
    editSearch,
    fields,
    MockServer,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
    validateSearch,
} from "@web/../tests/web_test_helpers";
import { RelationalModel } from "@web/model/relational_model/relational_model";

class Foo extends models.Model {
    name = fields.Char();
    bar = fields.Boolean();
    _records = [
        { id: 1, name: "a", bar: true },
        { id: 2, name: "b", bar: false },
        { id: 3, name: "c", bar: true },
    ];
}
defineWebModels();
defineModels([Foo]);

/** @returns {Promise<RelationalModel>} */
async function mountListAndGetModel(arch = `<list><field name="name"/></list>`) {
    /** @type {RelationalModel[]} */
    const instances = [];
    patchWithCleanup(RelationalModel.prototype, {
        setup(/** @type {any[]} */ ...args) {
            super.setup(...args);
            instances.push(/** @type {any} */ (this));
        },
    });
    await mountView({ resModel: "foo", type: "list", arch });
    return /** @type {RelationalModel} */ (instances.at(-1));
}

/** @param {RelationalModel} model */
const datapointIds = (model) => model.root.records.map((r) => r.id);

test("a reload keeps the datapoint of every record still in the page", async () => {
    const model = await mountListAndGetModel();
    const before = datapointIds(model);
    expect(before).toHaveLength(3);

    await model.root.load();
    expect(datapointIds(model)).toEqual(before);

    await model.load();
    expect(datapointIds(model)).toEqual(before);
    expect(queryAllTexts(".o_data_cell")).toEqual(["a", "b", "c"]);

    MockServer.env["foo"].write([1], { name: "a2" });
    await model.root.load();
    await animationFrame();
    expect(datapointIds(model)).toEqual(before);
    expect(queryAllTexts(".o_data_cell")).toEqual(["a2", "b", "c"]);
});

test("a reload rebuilds the page from the server payload, reusing what it can", async () => {
    const model = await mountListAndGetModel();
    const [dp1, dp2, dp3] = datapointIds(model);

    MockServer.env["foo"].create({ name: "d", bar: false });
    MockServer.env["foo"].write([2], { name: "b3" });
    await model.root.load({ domain: [["id", "!=", 3]] });
    await animationFrame();

    const ids = datapointIds(model);
    expect(ids).toHaveLength(3);
    expect(ids[0]).toBe(dp1);
    expect(ids[1]).toBe(dp2);
    expect(ids[2]).not.toBe(dp3);
    expect(model.root.records.map((r) => r.resId)).toEqual([1, 2, 4]);
    expect(queryAllTexts(".o_data_cell")).toEqual(["a", "b3", "d"]);
});

test("a reload drops the selection but keeps the datapoints", async () => {
    const model = await mountListAndGetModel();
    const before = datapointIds(model);
    model.root.records[1].toggleSelection(true);
    await animationFrame();
    expect(model.root.selection).toHaveLength(1);
    expect(model.root.records[1].selected).toBe(true);

    await model.root.load();
    await animationFrame();
    expect(datapointIds(model)).toEqual(before);
    expect(model.root.selection).toHaveLength(0);
    expect(model.root.records.every((record) => !record.selected)).toBe(true);
});

test("a record the user touched is rebuilt rather than reused", async () => {
    const model = await mountListAndGetModel(
        `<list editable="bottom"><field name="name"/></list>`,
    );
    const [dp1, dp2, dp3] = datapointIds(model);
    const edited = model.root.records[0];
    await edited.switchMode("edit");
    await edited.update({ name: "a-edited" });
    expect(edited.dirty).toBe(true);

    await model.root.load();
    const ids = datapointIds(model);
    expect(ids[0]).not.toBe(dp1);
    expect(ids[1]).toBe(dp2);
    expect(ids[2]).toBe(dp3);
});

test("a record built for another field set is rebuilt", async () => {
    const model = await mountListAndGetModel();
    const before = datapointIds(model);
    model.config.activeFields = {
        ...model.config.activeFields,
        bar: { ...model.config.activeFields.name, name: "bar" },
    };
    await model.load();
    expect(datapointIds(model)).not.toEqual(before);
    expect(datapointIds(model)).toHaveLength(3);
});

test("a background refresh of an unchanged page reuses every datapoint", async () => {
    let reads = 0;
    onRpc("foo", "web_search_read", () => {
        reads++;
    });
    const model = await mountListAndGetModel();
    const before = datapointIds(model);
    expect(reads).toBe(1);

    model.root.setData({
        records: MockServer.env["foo"]
            .browse([1, 2, 3])
            .map((r) => ({ id: r.id, name: r.name })),
        length: 3,
    });
    expect(datapointIds(model)).toEqual(before);
});

test("a reloaded grouped list hands each group's records to the group that replaces it", async () => {
    /** @type {RelationalModel[]} */
    const instances = [];
    patchWithCleanup(RelationalModel.prototype, {
        setup(/** @type {any[]} */ ...args) {
            super.setup(...args);
            instances.push(/** @type {any} */ (this));
        },
    });
    await mountView({
        resModel: "foo",
        type: "kanban",
        groupBy: ["bar"],
        arch: `<kanban><templates><t t-name="card"><field name="name"/></t></templates></kanban>`,
    });
    const model = /** @type {RelationalModel} */ (instances.at(-1));
    const idsByGroup = () =>
        Object.fromEntries(
            model.root.groups.map((g) => [
                String(g.value),
                g.list.records.map((r) => r.id),
            ]),
        );
    const before = idsByGroup();
    expect(Object.values(before).flat()).toHaveLength(3);
    expect(queryAllTexts(".o_kanban_record:not(.o_kanban_ghost)")).toEqual([
        "b",
        "a",
        "c",
    ]);

    MockServer.env["foo"].write([1], { name: "a2" });
    await model.load();
    await animationFrame();
    expect(idsByGroup()).toEqual(before);
    expect(queryAllTexts(".o_kanban_record:not(.o_kanban_ghost)")).toEqual([
        "b",
        "a2",
        "c",
    ]);

    await model.root.load();
    await animationFrame();
    expect(idsByGroup()).toEqual(before);
});

test("a real load after a sample load adopts nothing from the sample root", async () => {
    Foo._records = [];
    /** @type {RelationalModel[]} */
    const instances = [];
    patchWithCleanup(RelationalModel.prototype, {
        setup(/** @type {any[]} */ ...args) {
            super.setup(...args);
            instances.push(/** @type {any} */ (this));
        },
    });
    await mountView({
        resModel: "foo",
        type: "kanban",
        arch: `<kanban sample="1"><templates><t t-name="card"><field name="name"/></t></templates></kanban>`,
        searchViewArch: `<search><field name="name"/></search>`,
    });
    const model = /** @type {RelationalModel} */ (instances.at(-1));
    expect(model.useSampleModel).toBe(true);
    expect(".o_view_sample_data").toHaveCount(1);
    const sampleIds = model.root.records.map((r) => r.id);
    expect(sampleIds.length).toBeGreaterThan(0);

    const realId = MockServer.env["foo"].create({ name: "real", bar: true });
    expect(model.root.records.map((record) => record.resId)).toInclude(realId);
    await editSearch("real");
    await validateSearch();
    await animationFrame();
    expect(model.useSampleModel).toBe(false);
    expect(".o_view_sample_data").toHaveCount(0);
    expect(model.root.records).toHaveLength(1);
    expect(sampleIds).not.toInclude(model.root.records[0].id);
    expect(queryAllTexts(".o_kanban_record:not(.o_kanban_ghost)")).toEqual(["real"]);
});
