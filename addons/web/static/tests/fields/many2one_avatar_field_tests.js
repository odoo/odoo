/** @odoo-module **/

import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { browser } from "@web/core/browser/browser";
import {
    click,
    clickEdit,
    clickSave,
    editInput,
    getFixture,
    getNodesTextContent,
    patchWithCleanup,
    selectDropdownItem,
} from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        int_field: { string: "int_field", type: "integer" },
                        user_id: { string: "User", type: "many2one", relation: "user" },
                    },
                    records: [
                        { id: 1, user_id: 17 },
                        { id: 2, user_id: 19 },
                        { id: 3, user_id: 17 },
                        { id: 4, user_id: false },
                    ],
                },
                user: {
                    fields: {
                        name: { string: "Name", type: "char" },
                        partner_ids: {
                            type: "one2many",
                            relation: "partner",
                            relation_field: "user_id",
                        },
                    },
                    records: [
                        {
                            id: 17,
                            name: "Aline",
                        },
                        {
                            id: 19,
                            name: "Christine",
                        },
                    ],
                },
            },
        };

        setupViewRegistries();

        patchWithCleanup(AutoComplete, {
            delay: 0,
        });
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });
    });

    QUnit.module("Many2OneAvatar");

    QUnit.test("basic form view flow", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
                <form>
                    <field name="user_id" widget="many2one_avatar"/>
                </form>`,
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=user_id]").textContent.trim(),
            "Aline"
        );
        assert.containsOnce(
            target,
            '.o_m2o_avatar > img[data-src="/web/image/user/17/avatar_128"]'
        );

        await clickEdit(target);

        assert.containsOnce(target, ".o_input_dropdown");
        assert.strictEqual(target.querySelector(".o_input_dropdown input").value, "Aline");
        assert.containsOnce(target, ".o_external_button");
        assert.containsOnce(
            target,
            '.o_m2o_avatar > img[data-src="/web/image/user/17/avatar_128"]'
        );

        await selectDropdownItem(target, "user_id", "Christine");

        assert.containsOnce(
            target,
            '.o_m2o_avatar > img[data-src="/web/image/user/19/avatar_128"]'
        );
        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=user_id]").textContent.trim(),
            "Christine"
        );
        assert.containsOnce(
            target,
            '.o_m2o_avatar > img[data-src="/web/image/user/19/avatar_128"]'
        );

        await clickEdit(target);
        await editInput(target, '.o_field_widget[name="user_id"] input', "");

        assert.containsNone(target, ".o_m2o_avatar > img");
        assert.containsOnce(target, ".o_m2o_avatar > .o_m2o_avatar_empty");
        await clickSave(target);

        assert.containsNone(target, ".o_m2o_avatar > img");
        assert.containsNone(target, ".o_m2o_avatar > .o_m2o_avatar_empty");
    });

    QUnit.test("onchange in form view flow", async function (assert) {
        serverData.models.partner.onchanges = {
            int_field: function (obj) {
                if (obj.int_field === 1) {
                    obj.user_id = [19, "Christine"];
                } else if (obj.int_field === 2) {
                    obj.user_id = false;
                } else {
                    obj.user_id = [17, "Aline"]; // default value
                }
            },
        };

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            arch: `
                <form>
                    <field name="int_field"/>
                    <field name="user_id" widget="many2one_avatar" readonly="1"/>
                </form>`,
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=user_id]").textContent.trim(),
            "Aline"
        );
        assert.containsOnce(
            target,
            '.o_m2o_avatar > img[data-src="/web/image/user/17/avatar_128"]'
        );

        await editInput(target, "div[name=int_field] input", 1);

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=user_id]").textContent.trim(),
            "Christine"
        );
        assert.containsOnce(
            target,
            '.o_m2o_avatar > img[data-src="/web/image/user/19/avatar_128"]'
        );

        await editInput(target, "div[name=int_field] input", 2);

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=user_id]").textContent.trim(),
            ""
        );
        assert.containsNone(target, ".o_m2o_avatar > img");
    });

    QUnit.test("basic list view flow", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "list",
            serverData,
            resModel: "partner",
            arch: `<tree><field name="user_id" widget="many2one_avatar"/></tree>`,
        });

        assert.strictEqual(
            getNodesTextContent(target.querySelectorAll(".o_data_cell span")),
            "AlineChristineAline"
        );

        const sources = (function* expectedSources() {
            yield "/web/image/user/17/avatar_128";
            yield "/web/image/user/19/avatar_128";
            yield "/web/image/user/17/avatar_128";
        })();

        const imgs = target.querySelectorAll(".o_m2o_avatar > img");
        for (const image of imgs) {
            assert.strictEqual(image.dataset.src, sources.next().value);
        }
    });

    QUnit.test("basic flow in editable list view", async function (assert) {
        await makeView({
            type: "list",
            serverData,
            resModel: "partner",
            arch: `<tree editable="top"><field name="user_id" widget="many2one_avatar"/></tree>`,
        });

        assert.strictEqual(
            getNodesTextContent(target.querySelectorAll(".o_data_cell span")),
            "AlineChristineAline"
        );

        const sources = (function* expectedSources() {
            yield "/web/image/user/17/avatar_128";
            yield "/web/image/user/19/avatar_128";
            yield "/web/image/user/17/avatar_128";
        })();

        const imgs = target.querySelectorAll(".o_m2o_avatar > img");
        for (const image of imgs) {
            assert.strictEqual(image.dataset.src, sources.next().value);
        }

        await click(target.querySelectorAll(".o_data_row .o_data_cell")[0]);

        assert.strictEqual(
            target.querySelector(".o_m2o_avatar > img").dataset.src,
            "/web/image/user/17/avatar_128"
        );
    });
});
