/* @odoo-module */

import {
    click,
    clickSave,
    editInput,
    getFixture,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import {
    defaultLocalization,
    makeFakeLocalizationService,
} from "@web/../tests/helpers/mock_services";
import {makeView, setupViewRegistries} from "@web/../tests/views/helpers";
import {localization} from "@web/core/l10n/localization";
import {registry} from "@web/core/registry";

const {QUnit} = window;

QUnit.module("FieldNumericFormatting", (hooks) => {
    let target = {};
    let serverData = {};
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        int_field: {string: "int_field", type: "integer"},
                        float_field: {string: "Float field", type: "float"},
                    },
                    records: [
                        {id: 1, int_field: 10, float_field: 0.36},
                        {id: 3, int_field: 8069, float_field: 8069},
                    ],
                },
            },
        };
        setupViewRegistries();
    });
    QUnit.test(
        "Float field with enable_formatting option as false",
        async function (assert) {
            registry.category("services").remove("localization");
            registry
                .category("services")
                .add(
                    "localization",
                    makeFakeLocalizationService({thousandsSep: ",", grouping: [3, 0]})
                );

            await makeView({
                type: "form",
                serverData,
                resModel: "partner",
                resId: 1,
                arch: `<form><field name="float_field" options="{'enable_formatting': false}"/></form>`,
            });

            assert.strictEqual(
                target.querySelector(".o_field_widget input").value,
                "0.36",
                "Integer value must not be formatted"
            );

            await editInput(
                target,
                ".o_field_widget[name=float_field] input",
                "123456.789"
            );
            await clickSave(target);
            assert.strictEqual(
                target.querySelector(".o_field_widget input").value,
                "123456.789",
                "Integer value must be not formatted if input type is number."
            );
        }
    );
    QUnit.test(
        "Float field with enable_formatting option as false in editable list view",
        async function (assert) {
            await makeView({
                serverData,
                type: "list",
                resModel: "partner",
                arch: `
                <tree editable="bottom">
                    <field name="float_field" widget="float" digits="[5,3]" options="{'enable_formatting': false}" />
                </tree>`,
            });

            // Switch to edit mode
            await click(
                target.querySelector("tr.o_data_row td:not(.o_list_record_selector)")
            );

            assert.containsOnce(
                target,
                'div[name="float_field"] input',
                "The view should have 1 input for editable float."
            );

            await editInput(
                target,
                'div[name="float_field"] input',
                "108.2458938598598"
            );
            assert.strictEqual(
                target.querySelector('div[name="float_field"] input').value,
                "108.2458938598598",
                "The value should not be formatted on blur."
            );

            await editInput(
                target,
                'div[name="float_field"] input',
                "18.8958938598598"
            );
            await click(target.querySelector(".o_list_button_save"));
            assert.strictEqual(
                target.querySelector(".o_field_widget").textContent,
                "18.8958938598598",
                "The new value should not be rounded as well."
            );
        }
    );
    QUnit.test(
        "IntegerField with enable_formatting option as false",
        async function (assert) {
            patchWithCleanup(localization, {...defaultLocalization, grouping: [3, 0]});

            await makeView({
                type: "form",
                serverData,
                resModel: "partner",
                resId: 3,
                arch: `<form><field name="int_field" options="{'enable_formatting': false}"/></form>`,
            });

            assert.strictEqual(
                target.querySelector(".o_field_widget input").value,
                "8069",
                "Integer value must not be formatted"
            );

            await editInput(
                target,
                ".o_field_widget[name=int_field] input",
                "1234567890"
            );
            await clickSave(target);
            assert.strictEqual(
                target.querySelector(".o_field_widget input").value,
                "1234567890",
                "Integer value must be not formatted if input type is number."
            );
        }
    );
});
