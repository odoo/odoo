import { describe, expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    models,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { ModelSelector } from "@web/core/model_selector/model_selector";

class IrModel extends models.Model {
    _name = "ir.model";

    name = fields.Char({ string: "Model Name" });
    model = fields.Char();

    _records = [{ id: 1, name: "Model 1", model: "model.1" }];
}

defineModels([IrModel]);
describe.current.tags("mobile");

onRpc("ir.model", "display_name_for", function ({ args }) {
    const models = args[0];
    return this.env["ir.model"]
        .filter((record) => models.includes(record.model))
        .map((record) => ({
            model: record.model,
            display_name: record.name,
        }));
});

test("model selector remains interactive on mobile", async () => {
    await mountWithCleanup(ModelSelector, {
        props: {
            models: ["model.1"],
            placeholder: "No linked record",
            onModelSelected: (selected) => {
                expect.step("model selected");
                expect(selected).toEqual({
                    label: "Model 1",
                    technical: "model.1",
                });
            },
        },
    });

    expect(".o-autocomplete--input").not.toHaveAttribute("readonly");
    expect(".o-autocomplete--input").toHaveAttribute("placeholder", "No linked record");

    await contains(".o-autocomplete--input").click();
    await contains(".o_model_selector_model_1").click();

    expect.verifySteps(["model selected"]);
});
