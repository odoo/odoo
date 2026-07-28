/** @odoo-module **/

import { getFixture, getNodesTextContent } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        res_id: {
                            string: "Ressource Id",
                            type: "many2one_reference",
                        },
                    },
                    records: [
                        { id: 1, res_id: 10 },
                        { id: 2, res_id: false },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("Many2OneReferenceField");

    QUnit.test("Many2OneReferenceField in form view", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: '<form><field name="res_id"/></form>',
        });

        assert.strictEqual(target.querySelector(".o_field_widget input").value, "10");
    });

    QUnit.test("Many2OneReferenceField in list view", async function (assert) {
        await makeView({
            type: "list",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: '<list><field name="res_id"/></list>',
        });

        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell")), ["10", ""]);
    });

    QUnit.test("should be 0 when unset", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 2,
            arch: '<form><field name="res_id"/></form>',
        });

        assert.strictEqual(target.querySelector(".o_field_widget input").value, "");
    });
});
