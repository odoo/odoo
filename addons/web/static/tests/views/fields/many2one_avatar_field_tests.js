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
    clickOpenedDropdownItem,
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
        assert.containsOnce(target, ".o_field_many2one_avatar > div");

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
            getNodesTextContent(target.querySelectorAll(".o_data_cell[name='user_id']")),
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
            getNodesTextContent(target.querySelectorAll(".o_data_cell[name='user_id']")),
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
            arch: '<form><field name="user_id" widget="many2one_avatar" placeholder="Placeholder"/></form>',
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
        await click(target.querySelector(".o_data_row .o_data_cell [name='user_id']"));
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
        await click(target.querySelector(".o_data_row .o_data_cell [name='user_id']"));
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

        await click(target.querySelector(".o_data_row .o_data_cell [name='user_id']"));
        assert.containsNone(target, ".o_selected_row");

        assert.verifySteps(["openRecord"]);
    });

    QUnit.test(
        "readonly many2one_avatar in form view should contain a link",
        async function (assert) {
            await makeView({
                type: "form",
                serverData,
                resModel: "partner",
                resId: 1,
                arch: `<form><field name="user_id" widget="many2one_avatar" readonly="1"/></form>`,
            });

            assert.containsOnce(target, "[name='user_id'] a");
        }
    );

    QUnit.test(
        "readonly many2one_avatar in list view should not contain a link",
        async function (assert) {
            await makeView({
                type: "list",
                serverData,
                resModel: "partner",
                arch: `<tree><field name="user_id" widget="many2one_avatar"/></tree>`,
            });

            assert.containsNone(target, "[name='user_id'] a");
        }
    );

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
        await clickOpenedDropdownItem(target, "user_id", "Create and edit...");

        await clickDiscard(target.querySelector(".modal"));
        assert.strictEqual(target.querySelector(".o_field_widget[name=user_id] input").value, "");
        assert.containsOnce(target, ".o_field_widget[name=user_id] span.o_m2o_avatar_empty");
    });

    QUnit.test("widget many2one_avatar in kanban view (load more dialog)", async function (assert) {
        assert.expect(1);

        for (let id = 1; id <= 10; id++) {
            serverData.models.user.records.push({
                id,
                display_name: `record ${id}`,
            });
        }

        serverData.views = {
            "user,false,list": '<tree><field name="display_name"/></tree>',
            "user,false,search": "<search/>",
        };
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div class="oe_kanban_global_click">
                                <div class="oe_kanban_footer">
                                    <div class="o_kanban_record_bottom">
                                        <div class="oe_kanban_bottom_right">
                                            <field name="user_id" widget="many2one_avatar"/>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });

        // open popover
        await click(
            target.querySelector(
                ".o_kanban_record:nth-child(4) .o_field_many2one_avatar .o_m2o_avatar > a.o_quick_assign"
            )
        );

        // load more
        await click(
            document.querySelector(".o-overlay-container .o_m2o_dropdown_option_search_more")
        );
        await click(document.querySelector(".o_dialog .o_list_table .o_data_row .o_data_cell"));
        assert.strictEqual(
            target.querySelector(
                ".o_kanban_record:nth-child(4) .o_field_many2one_avatar .o_m2o_avatar > img"
            ).dataset.src,
            "/web/image/user/1/avatar_128",
            "should have correct avatar image"
        );
    });

    QUnit.test("widget many2one_avatar in kanban view", async function (assert) {
        assert.expect(5);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div class="oe_kanban_global_click">
                                <div class="oe_kanban_footer">
                                    <div class="o_kanban_record_bottom">
                                        <div class="oe_kanban_bottom_right">
                                            <field name="user_id" widget="many2one_avatar"/>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });
        assert.strictEqual(
            target.querySelector(
                ".o_kanban_record:nth-child(1) .o_field_many2one_avatar .o_m2o_avatar > img"
            ).dataset.src,
            "/web/image/user/17/avatar_128",
            "should have correct avatar image"
        );
        assert.containsOnce(
            target,
            ".o_kanban_record:nth-child(4) .o_field_many2one_avatar .o_m2o_avatar > .o_quick_assign",
            "should have the quick assign icon"
        );
        // open popover
        await click(
            target.querySelector(
                ".o_kanban_record:nth-child(4) .o_field_many2one_avatar .o_m2o_avatar > .o_quick_assign"
            )
        );
        const popover = document.querySelector(".o-overlay-container");
        assert.strictEqual(
            document.activeElement,
            popover.querySelector("input"),
            "the input inside the popover should have the focus"
        );
        // select first input
        await click(popover.querySelector(".o-autocomplete--dropdown-item"));
        assert.strictEqual(
            target.querySelector(
                ".o_kanban_record:nth-child(4) .o_field_many2one_avatar .o_m2o_avatar > img"
            ).dataset.src,
            "/web/image/user/17/avatar_128",
            "should have correct avatar image"
        );
        assert.containsNone(
            target,
            ".o_kanban_record:nth-child(4) .o_field_many2one_avatar .o_m2o_avatar > .o_quick_assign",
            "should not have the quick assign icon"
        );
    });

    QUnit.test(
        "widget many2one_avatar in kanban view without access rights",
        async function (assert) {
            assert.expect(2);
            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch: `
                <kanban edit="0" create="0">
                    <templates>
                        <t t-name="kanban-box">
                            <div class="oe_kanban_global_click">
                                <div class="oe_kanban_footer">
                                    <div class="o_kanban_record_bottom">
                                        <div class="oe_kanban_bottom_right">
                                            <field name="user_id" widget="many2one_avatar"/>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            });
            assert.strictEqual(
                target.querySelector(
                    ".o_kanban_record:nth-child(1) .o_field_many2one_avatar .o_m2o_avatar > img"
                ).dataset.src,
                "/web/image/user/17/avatar_128",
                "should have correct avatar image"
            );
            assert.containsNone(
                target,
                ".o_kanban_record:nth-child(4) .o_field_many2one_avatar .o_m2o_avatar > .o_quick_assign",
                "should not have the quick assign icon"
            );
        }
    );
});
