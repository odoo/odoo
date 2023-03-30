/** @odoo-module **/

import {
    click,
    clickSave,
    editInput,
    getFixture,
    getNodesTextContent,
    patchWithCleanup,
    selectDropdownItem,
    triggerEvent,
    clickDiscard,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

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
            target.querySelector(".o_field_widget[name=user_id] input").value,
            "Aline"
        );
        assert.containsOnce(
            target,
            '.o_m2o_avatar > img[data-src="/web/image/user/17/avatar_128"]'
        );
        assert.containsOnce(target, '.o_field_many2one_avatar > div[data-tooltip="Aline"]');

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
            target.querySelector(".o_field_widget[name=user_id] input").value,
            "Christine"
        );
        assert.containsOnce(
            target,
            '.o_m2o_avatar > img[data-src="/web/image/user/19/avatar_128"]'
        );

        await editInput(target, '.o_field_widget[name="user_id"] input', "");

        assert.containsNone(target, ".o_m2o_avatar > img");
        assert.containsOnce(target, ".o_m2o_avatar > .o_m2o_avatar_empty");
        await clickSave(target);

        assert.containsNone(target, ".o_m2o_avatar > img");
        assert.containsOnce(target, ".o_m2o_avatar > .o_m2o_avatar_empty");
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
        await makeView({
            type: "list",
            serverData,
            resModel: "partner",
            arch: '<tree><field name="user_id" widget="many2one_avatar"/></tree>',
        });

        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_data_cell[name='user_id'] span span")),
            ["Aline", "Christine", "Aline", ""]
        );
        const imgs = target.querySelectorAll(".o_m2o_avatar > img");
        assert.strictEqual(imgs[0].dataset.src, "/web/image/user/17/avatar_128");
        assert.strictEqual(imgs[1].dataset.src, "/web/image/user/19/avatar_128");
        assert.strictEqual(imgs[2].dataset.src, "/web/image/user/17/avatar_128");
    });

    QUnit.test("basic flow in editable list view", async function (assert) {
        await makeView({
            type: "list",
            serverData,
            resModel: "partner",
            arch: '<tree editable="top"><field name="user_id" widget="many2one_avatar"/></tree>',
        });

        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_data_cell[name='user_id'] span span")),
            ["Aline", "Christine", "Aline", ""]
        );

        const imgs = target.querySelectorAll(".o_m2o_avatar > img");
        assert.strictEqual(imgs[0].dataset.src, "/web/image/user/17/avatar_128");
        assert.strictEqual(imgs[1].dataset.src, "/web/image/user/19/avatar_128");
        assert.strictEqual(imgs[2].dataset.src, "/web/image/user/17/avatar_128");

        await click(target.querySelectorAll(".o_data_row .o_data_cell")[0]);

        assert.strictEqual(
            target.querySelector(".o_m2o_avatar > img").dataset.src,
            "/web/image/user/17/avatar_128"
        );
    });

    QUnit.test("Many2OneAvatar with placeholder", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch:
                '<form><field name="user_id" widget="many2one_avatar" placeholder="Placeholder"/></form>',
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget[name='user_id'] input").placeholder,
            "Placeholder"
        );
    });

    QUnit.test("click on many2one_avatar in a list view (multi_edit='1')", async function (assert) {
        const listView = registry.category("views").get("list");
        patchWithCleanup(listView.Controller.prototype, {
            openRecord() {
                assert.step("openRecord");
            },
        });

        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree multi_edit="1">
                    <field name="user_id" widget="many2one_avatar"/>
                </tree>`,
        });

        await click(target.querySelectorAll(".o_data_row")[0], ".o_list_record_selector input");
        await click(target.querySelector(".o_data_row .o_data_cell [name='user_id'] span span"));
        assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");

        assert.verifySteps([]);
    });

    QUnit.test("click on many2one_avatar in an editable list view", async function (assert) {
        const listView = registry.category("views").get("list");
        patchWithCleanup(listView.Controller.prototype, {
            openRecord() {
                assert.step("openRecord");
            },
        });

        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="user_id" widget="many2one_avatar"/>
                </tree>`,
        });

        await click(target.querySelectorAll(".o_data_row")[0], ".o_list_record_selector input");
        await click(target.querySelector(".o_data_row .o_data_cell [name='user_id'] span span"));
        assert.hasClass(target.querySelector(".o_data_row"), "o_selected_row");

        assert.verifySteps([]);
    });

    QUnit.test("click on many2one_avatar in an editable list view", async function (assert) {
        const listView = registry.category("views").get("list");
        patchWithCleanup(listView.Controller.prototype, {
            openRecord() {
                assert.step("openRecord");
            },
        });

        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree>
                    <field name="user_id" widget="many2one_avatar"/>
                </tree>`,
        });

        await click(target.querySelector(".o_data_row .o_data_cell [name='user_id'] span span"));
        assert.containsNone(target, ".o_selected_row");

        assert.verifySteps(["openRecord"]);
    });

    QUnit.test("cancelling create dialog should clear value in the field", async function (assert) {
        serverData.views = {
            "user,false,form": `
                <form>
                    <field name="name" />
                </form>`,
        };

        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree editable="top">
                    <field name="user_id" widget="many2one_avatar"/>
                </tree>`,
        });

        await click(target.querySelectorAll(".o_data_cell")[0]);
        const input = target.querySelector(".o_field_widget[name=user_id] input");
        input.value = "yy";
        await triggerEvent(input, null, "input");
        await click(target, ".o_field_widget[name=user_id] input");
        await selectDropdownItem(target, "user_id", "Create and edit...");

        await clickDiscard(target.querySelector(".modal"));
        assert.strictEqual(target.querySelector(".o_field_widget[name=user_id] input").value, "");
        assert.containsOnce(target, ".o_field_widget[name=user_id] span.o_m2o_avatar_empty");
    });
});
