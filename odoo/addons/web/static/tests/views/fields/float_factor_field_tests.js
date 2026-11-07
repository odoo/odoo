/** @odoo-module **/

import { registry } from "@web/core/registry";
import { clickSave, editInput, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: { qux: { string: "Qux", type: "float", digits: [16, 1] } },
                    records: [{ id: 1, qux: 9.1 }],
                    onchanges: {},
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("FloatFactorField");

    QUnit.test("FloatFactorField in form view", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="qux" widget="float_factor" options="{'factor': 0.5}" digits="[16,2]" />
                    </sheet>
                </form>`,
            mockRPC(route, { args }) {
                if (route === "/web/dataset/call_kw/partner/web_save") {
                    // 2.3 / 0.5 = 4.6
                    assert.strictEqual(args[1].qux, 4.6, "the correct float value should be saved");
                }
            },
        });
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='qux'] input").value,
            "4.55",
            "The value should be rendered correctly in the input."
        );

        await editInput(target, ".o_field_widget[name='qux'] input", "2.3");
        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "2.30",
            "The new value should be saved and displayed properly."
        );
    });

    QUnit.test("FloatFactorField comma as decimal point", async function (assert) {
        assert.expect(3);
        registry.category("services").remove("localization");
        registry.category("services").add(
            "localization",
            makeFakeLocalizationService({
                decimalPoint: ",",
                thousandsSep: "",
            })
        );

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="qux" widget="float_factor" options="{'factor': 0.5}" digits="[16,2]" />
                    </sheet>
                </form>`,
            mockRPC(route, { args }) {
                if (route === "/web/dataset/call_kw/partner/web_save") {
                    // 2.3 / 0.5 = 4.6
                    assert.strictEqual(args[1].qux, 4.6, "the correct float value should be saved");
                    assert.step("save");
                }
            },
        });

        await editInput(target, ".o_field_widget[name='qux'] input", "2,3");
        await clickSave(target);

        assert.verifySteps(["save"]);
    });
});
