import { expect, test } from "@odoo/hoot";

import { defineModels, models, fields, makeKwArgs } from "@web/../tests/web_test_helpers";
import { startServer, defineMailModels } from "./mail_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

class TestModel extends models.Model {
    _name = "test.model";

    name = fields.Char({ string: "Name" });
    other = fields.One2many({
        relation: "test.model2",
        string: "Other",
    });

    _to_store(store, fields) {
        store._add_record_fields(
            this,
            fields.filter((f) => f !== "name")
        );
        for (const model of this) {
            if (fields.includes("name")) {
                store._add_record_fields(this.browse(model.id), {
                    name: model.name,
                    test: "test",
                });
            }
        }
    }

    get _to_store_defaults() {
        return [
            "name",
            mailDataHelpers.Store.many(
                "other",
                makeKwArgs({
                    fields: ["name"],
                })
            ),
        ];
    }
}

class TestModel2 extends models.Model {
    _name = "test.model2";

    name = fields.Char({ string: "Name" });
    first = fields.Many2one({
        relation: "test.model",
        string: "First",
    });
}

defineMailModels();
defineModels({ TestModel, TestModel2 });

test("_to_store and _to_store_defaults are used correctly", async () => {
    const pyEnv = await startServer();
    const testModel = pyEnv["test.model"];
    const testModel2 = pyEnv["test.model2"];
    const [model1] = testModel.create([{ name: "Model 1" }]);
    const [model11] = testModel.create([{ name: "Model 11" }]);
    const [model2] = testModel2.create([{ name: "Model 2", first: model1 }]);
    testModel.write(model1, { other: [model2] });

    const store = new mailDataHelpers.Store();
    store.add(testModel.browse([model1, model11]));
    const result = store.get_result();
    expect(result["test.model"]).toEqual([
        {
            id: model1,
            name: "Model 1",
            test: "test",
            other: [model2],
        },
        {
            id: model11,
            name: "Model 11",
            test: "test",
            other: [],
        },
    ]);
    expect(result["test.model2"]).toEqual([
        {
            id: model2,
            name: "Model 2",
        },
    ]);
});

test("one2many relation is working properly", async () => {
    const pyEnv = await startServer();
    const testModel = pyEnv["test.model"];
    const testModel2 = pyEnv["test.model2"];

    const [model1] = testModel.create([{ name: "Model 1" }]);
    const [model2] = testModel2.create([{ name: "Model 2", first: model1 }]);
    testModel.write(model1, { other: [model2] });

    const store = new mailDataHelpers.Store();
    store.add(testModel2.browse(model2), [mailDataHelpers.Store.one("first", ["name"])]);

    expect(store.get_result()).toEqual({
        "test.model2": [
            {
                id: model2,
                first: model1,
            },
        ],
        "test.model": [
            {
                id: model1,
                name: "Model 1",
                test: "test",
            },
        ],
    });
});
