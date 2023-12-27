/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import {
    click,
    clickSave,
    getFixture,
    patchWithCleanup,
    selectDropdownItem,
    triggerEvent,
    editInput,
    clickOpenedDropdownItem,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { triggerHotkey } from "../../helpers/utils";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                    },
                    records: [
                        { id: 1, display_name: "first record" },
                        { id: 2, display_name: "second record" },
                        { id: 4, display_name: "aaa" },
                    ],
                    onchanges: {},
                },
                turtle: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        partner_ids: { string: "Partner", type: "many2many", relation: "partner" },
                    },
                    records: [
                        { id: 1, display_name: "leonardo", partner_ids: [] },
                        { id: 2, display_name: "donatello", partner_ids: [2, 4] },
                        { id: 3, display_name: "raphael" },
                    ],
                    onchanges: {},
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("Many2ManyTagsAvatarField");

    QUnit.test("widget many2many_tags_avatar", async function (assert) {
        await makeView({
            type: "form",
            resModel: "turtle",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="partner_ids" widget="many2many_tags_avatar"/>
                    </sheet>
                </form>`,
            resId: 2,
        });

        assert.containsN(
            target,
            ".o_field_many2many_tags_avatar.o_field_widget .o_avatar img",
            2,
            "should have 2 records"
        );
        assert.strictEqual(
            target.querySelector(".o_field_many2many_tags_avatar.o_field_widget .o_avatar img")
                .dataset.src,
            "/web/image/partner/2/avatar_128",
            "should have correct avatar image"
        );
    });

    QUnit.test("widget many2many_tags_avatar in list view", async function (assert) {
        const records = [];
        for (let id = 5; id <= 15; id++) {
            records.push({
                id,
                display_name: `record ${id}`,
            });
        }
        serverData.models.partner.records = serverData.models.partner.records.concat(records);

        serverData.models.turtle.records.push({
            id: 4,
            display_name: "crime master gogo",
            partner_ids: [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
        });
        serverData.models.turtle.records[0].partner_ids = [1];
        serverData.models.turtle.records[1].partner_ids = [1, 2, 4, 5, 6, 7];
        serverData.models.turtle.records[2].partner_ids = [1, 2, 4, 5, 7];

        await makeView({
            type: "list",
            resModel: "turtle",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="partner_ids" widget="many2many_tags_avatar"/>
                </tree>`,
        });
        assert.strictEqual(
            target.querySelector(".o_data_row .o_field_many2many_tags_avatar img.o_m2m_avatar")
                .dataset.src,
            "/web/image/partner/1/avatar_128",
            "should have correct avatar image"
        );
        assert.strictEqual(
            target
                .querySelector(
                    ".o_data_row .o_many2many_tags_avatar_cell .o_field_many2many_tags_avatar"
                )
                .textContent.trim(),
            "first record",
            "should display like many2one avatar if there is only one record"
        );
        assert.containsN(
            target,
            ".o_data_row:nth-child(2) .o_field_many2many_tags_avatar .o_avatar:not(.o_m2m_avatar_empty) img",
            4,
            "should have 4 records"
        );
        assert.containsN(
            target,
            ".o_data_row:nth-child(3) .o_field_many2many_tags_avatar .o_avatar:not(.o_m2m_avatar_empty) img",
            5,
            "should have 5 records"
        );
        assert.containsOnce(
            target,
            ".o_data_row:nth-child(2) .o_field_many2many_tags_avatar .o_m2m_avatar_empty",
            "should have o_m2m_avatar_empty span"
        );
        assert.strictEqual(
            target
                .querySelector(
                    ".o_data_row:nth-child(2) .o_field_many2many_tags_avatar .o_m2m_avatar_empty"
                )
                .textContent.trim(),
            "+2",
            "should have +2 in o_m2m_avatar_empty"
        );
        assert.strictEqual(
            target.querySelector(
                ".o_data_row:nth-child(2) .o_field_many2many_tags_avatar img.o_m2m_avatar"
            ).dataset.src,
            "/web/image/partner/1/avatar_128",
            "should have correct avatar image"
        );
        assert.strictEqual(
            target.querySelector(
                ".o_data_row:nth-child(2) .o_field_many2many_tags_avatar .o_avatar:nth-child(2) img.o_m2m_avatar"
            ).dataset.src,
            "/web/image/partner/2/avatar_128",
            "should have correct avatar image"
        );
        assert.strictEqual(
            target.querySelector(
                ".o_data_row:nth-child(2) .o_field_many2many_tags_avatar .o_avatar:nth-child(3) img.o_m2m_avatar"
            ).dataset.src,
            "/web/image/partner/4/avatar_128",
            "should have correct avatar image"
        );
        assert.strictEqual(
            target.querySelector(
                ".o_data_row:nth-child(2) .o_field_many2many_tags_avatar .o_avatar:nth-child(4) img.o_m2m_avatar"
            ).dataset.src,
            "/web/image/partner/5/avatar_128",
            "should have correct avatar image"
        );
        assert.containsNone(
            target,
            ".o_data_row:nth-child(3) .o_field_many2many_tags_avatar .o_m2m_avatar_empty",
            "should have o_m2m_avatar_empty span"
        );
        assert.containsN(
            target,
            ".o_data_row:nth-child(4) .o_field_many2many_tags_avatar .o_avatar:not(.o_m2m_avatar_empty) img",
            4,
            "should have 4 records"
        );
        assert.containsOnce(
            target,
            ".o_data_row:nth-child(4) .o_field_many2many_tags_avatar .o_m2m_avatar_empty",
            "should have o_m2m_avatar_empty span"
        );
        assert.strictEqual(
            target
                .querySelector(
                    ".o_data_row:nth-child(4) .o_field_many2many_tags_avatar .o_m2m_avatar_empty"
                )
                .textContent.trim(),
            "+9",
            "should have +9 in o_m2m_avatar_empty"
        );

        // check data-tooltip attribute (used by the tooltip service)
        const tag = target.querySelector(
            ".o_data_row:nth-child(2) .o_field_many2many_tags_avatar .o_m2m_avatar_empty"
        );
        assert.strictEqual(
            tag.dataset["tooltipTemplate"],
            "web.TagsList.Tooltip",
            "uses the proper tooltip template"
        );
        const tooltipInfo = JSON.parse(tag.dataset["tooltipInfo"]);
        assert.strictEqual(
            tooltipInfo.tags.map((tag) => tag.text).join(" "),
            "record 6 record 7",
            "shows a tooltip on hover"
        );

        await click(target.querySelector(".o_data_row .o_many2many_tags_avatar_cell"));
        assert.containsN(
            target,
            ".o_data_row.o_selected_row .o_many2many_tags_avatar_cell .o_avatar img",
            1,
            "should have 1 many2many badges in edit mode"
        );

        await selectDropdownItem(target, "partner_ids", "second record");
        await click(
            target.querySelector(
                ".o_control_panel_main_buttons .d-none.d-xl-inline-flex .o_list_button_save"
            )
        );
        assert.containsN(
            target,
            ".o_data_row:first-child .o_field_many2many_tags_avatar .o_avatar img",
            2,
            "should have 2 records"
        );

        // Select the first row and enter edit mode on the x2many field.
        await click(target, ".o_data_row:nth-child(1) .o_list_record_selector input");
        await click(target, ".o_data_row:nth-child(1) .o_data_cell");

        // Only the first row should have tags with delete buttons.
        assert.containsN(target, ".o_data_row:nth-child(1) .o_field_tags span .o_delete", 2);
        assert.containsNone(target, ".o_data_row:nth-child(2) .o_field_tags span .o_delete");
        assert.containsNone(target, ".o_data_row:nth-child(3) .o_field_tags span .o_delete");
        assert.containsNone(target, ".o_data_row:nth-child(4) .o_field_tags span .o_delete");
    });

    QUnit.test(
        "widget many2many_tags_avatar list view - don't crash on keyboard navigation",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "turtle",
                serverData,
                arch: /*xml*/ `
                    <tree editable="bottom">
                        <field name="partner_ids" widget="many2many_tags_avatar"/>
                    </tree>
                `,
            });

            // Select the 2nd row and enter edit mode on the x2many field.
            await click(target, ".o_data_row:nth-child(2) .o_list_record_selector input");
            await click(target, ".o_data_row:nth-child(2) .o_data_cell");

            // Pressing left arrow should focus on the right-most (second) tag.
            await triggerHotkey("arrowleft");
            assert.strictEqual(
                target.querySelector(".o_data_row:nth-child(2) .o_field_tags span:nth-child(2)"),
                document.activeElement
            );

            // Pressing left arrow again should not crash and should focus on the first tag.
            await triggerHotkey("arrowleft");
            assert.strictEqual(
                target.querySelector(".o_data_row:nth-child(2) .o_field_tags span:nth-child(1)"),
                document.activeElement
            );
        }
    );

    QUnit.test("widget many2many_tags_avatar in kanban view", async function (assert) {
        assert.expect(21);

        for (let id = 5; id <= 15; id++) {
            serverData.models.partner.records.push({
                id,
                display_name: `record ${id}`,
            });
        }

        serverData.models.turtle.records.push({
            id: 4,
            display_name: "crime master gogo",
            partner_ids: [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
        });
        serverData.models.turtle.records[0].partner_ids = [1];
        serverData.models.turtle.records[1].partner_ids = [1, 2, 4];
        serverData.models.turtle.records[2].partner_ids = [1, 2, 4, 5];
        serverData.views = {
            "turtle,false,form": '<form><field name="display_name"/></form>',
            "partner,false,list": '<tree><field name="display_name"/></tree>',
            "partner,false,search": "<search/>",
        };

        await makeView({
            type: "kanban",
            resModel: "turtle",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div class="oe_kanban_global_click">
                                <field name="display_name"/>
                                <div class="oe_kanban_footer">
                                    <div class="o_kanban_record_bottom">
                                        <div class="oe_kanban_bottom_right">
                                            <field name="partner_ids" widget="many2many_tags_avatar"/>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            selectRecord(recordId) {
                assert.strictEqual(
                    recordId,
                    1,
                    "should call its selectRecord prop with the clicked record"
                );
            },
        });
        assert.containsOnce(
            target,
            ".o_kanban_record:first-child .o_field_many2many_tags_avatar .o_quick_assign",
            "should have the assign icon"
        );

        assert.containsN(
            target,
            ".o_kanban_record:nth-child(2) .o_field_many2many_tags_avatar .o_avatar img",
            2,
            "should have 2 records"
        );
        assert.containsN(
            target,
            ".o_kanban_record:nth-child(3) .o_field_many2many_tags_avatar .o_avatar img",
            2,
            "should have 2 records"
        );
        assert.strictEqual(
            target.querySelector(
                ".o_kanban_record:nth-child(3) .o_field_many2many_tags_avatar img.o_m2m_avatar"
            ).dataset.src,
            "/web/image/partner/5/avatar_128",
            "should have correct avatar image"
        );
        assert.strictEqual(
            target.querySelectorAll(
                ".o_kanban_record:nth-child(3) .o_field_many2many_tags_avatar img.o_m2m_avatar"
            )[1].dataset.src,
            "/web/image/partner/4/avatar_128",
            "should have correct avatar image"
        );
        assert.containsOnce(
            target,
            ".o_kanban_record:nth-child(3) .o_field_many2many_tags_avatar .o_m2m_avatar_empty",
            "should have o_m2m_avatar_empty span"
        );
        assert.strictEqual(
            target
                .querySelector(
                    ".o_kanban_record:nth-child(3) .o_field_many2many_tags_avatar .o_m2m_avatar_empty"
                )
                .textContent.trim(),
            "+2",
            "should have +2 in o_m2m_avatar_empty"
        );

        assert.containsN(
            target,
            ".o_kanban_record:nth-child(4) .o_field_many2many_tags_avatar .o_avatar img",
            2,
            "should have 2 records"
        );
        assert.containsOnce(
            target,
            ".o_kanban_record:nth-child(4) .o_field_many2many_tags_avatar .o_m2m_avatar_empty",
            "should have o_m2m_avatar_empty span"
        );
        assert.strictEqual(
            target
                .querySelector(
                    ".o_kanban_record:nth-child(4) .o_field_many2many_tags_avatar .o_m2m_avatar_empty"
                )
                .textContent.trim(),
            "9+",
            "should have 9+ in o_m2m_avatar_empty"
        );
        assert.containsNone(target, ".o_field_many2many_tags_avatar .o_field_many2many_selection");

        const o_kanban_record = target.querySelector(".o_kanban_record:nth-child(2)");
        await click(o_kanban_record, ".o_field_tags > .o_m2m_avatar_empty");
        const popover = document.querySelector(".o-overlay-container");
        assert.strictEqual(
            document.activeElement,
            popover.querySelector("input"),
            "the input inside the popover should have the focus"
        );
        assert.strictEqual(popover.querySelectorAll(".o_tag").length, 3, "Should have 3 tags");
        // delete inside the popover
        await click(popover.querySelector(".o_tag .o_delete"));
        assert.strictEqual(popover.querySelectorAll(".o_tag").length, 2, "Should have 2 tag");
        assert.strictEqual(
            o_kanban_record.querySelectorAll(".o_tag").length,
            2,
            "Should have 2 tags"
        );
        // select first input
        await click(popover.querySelector(".o-autocomplete--dropdown-item"));
        assert.strictEqual(popover.querySelectorAll(".o_tag").length, 3, "Should have 3 tags");
        assert.strictEqual(
            o_kanban_record.querySelectorAll(".o_tag").length,
            2,
            "Should have 2 tags"
        );
        // load more
        await click(popover.querySelector(".o_m2o_dropdown_option_search_more"));
        // first item
        await click(document.querySelector(".o_dialog .o_list_table .o_data_row .o_data_cell"));
        assert.strictEqual(popover.querySelectorAll(".o_tag").length, 4, "Should have 4 tags");
        assert.strictEqual(
            o_kanban_record.querySelectorAll(".o_tag").length,
            2,
            "Should have 2 tags"
        );
        assert.strictEqual(
            o_kanban_record.querySelector("img.o_m2m_avatar").dataset.src,
            "/web/image/partner/4/avatar_128",
            "should have correct avatar image"
        );
        await click(
            target.querySelector(".o_kanban_record .o_field_many2many_tags_avatar img.o_m2m_avatar")
        );
    });

    QUnit.test(
        "widget many2many_tags_avatar add/remove tags in kanban view",
        async function (assert) {
            assert.expect(3);

            await makeView({
                type: "kanban",
                resModel: "turtle",
                serverData,
                arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div class="oe_kanban_global_click">
                                <field name="display_name"/>
                                <div class="oe_kanban_footer">
                                    <div class="o_kanban_record_bottom">
                                        <div class="oe_kanban_bottom_right">
                                            <field name="partner_ids" widget="many2many_tags_avatar"/>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
                async mockRPC(route, { method, args }) {
                    if (method === "web_save") {
                        const command = args[1].partner_ids[0];
                        assert.step(`web_save: ${command[0]}-${command[1]}`);
                    }
                },
            });
            await click(target, ".o_kanban_record:first-child .o_quick_assign");
            // add and directly remove an item
            await click(target, ".o_popover .o-autocomplete--dropdown-item:first-child");
            await click(target, ".o_popover .o_tag .o_delete");
            assert.verifySteps(["web_save: 4-1", "web_save: 3-1"]);
        }
    );

    QUnit.test("widget many2many_tags_avatar delete tag", async function (assert) {
        await makeView({
            type: "form",
            resModel: "turtle",
            resId: 2,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="partner_ids" widget="many2many_tags_avatar"/>
                    </sheet>
                </form>`,
        });

        assert.containsN(
            target,
            ".o_field_many2many_tags_avatar.o_field_widget .o_tag",
            2,
            "should have 2 records"
        );

        await click(
            target.querySelector(".o_field_many2many_tags_avatar.o_field_widget .o_tag .o_delete")
        );
        assert.containsOnce(
            target,
            ".o_field_many2many_tags_avatar.o_field_widget .o_tag",
            "should have 1 record"
        );

        await clickSave(target);
        assert.containsOnce(
            target,
            ".o_field_many2many_tags_avatar.o_field_widget .o_tag",
            "should have 1 record"
        );
    });

    QUnit.test(
        "widget many2many_tags_avatar quick add tags and close in kanban view with keyboard navigation",
        async function (assert) {
            await makeView({
                type: "kanban",
                resModel: "turtle",
                serverData,
                arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div class="oe_kanban_global_click">
                                <field name="display_name"/>
                                <div class="oe_kanban_footer">
                                    <div class="o_kanban_record_bottom">
                                        <div class="oe_kanban_bottom_right">
                                            <field name="partner_ids" widget="many2many_tags_avatar"/>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            });
            await click(target, ".o_kanban_record:first-child .o_quick_assign");
            // add and directly close the dropdown
            await triggerEvent(target, null, "keydown", { key: "Tab" });
            await triggerEvent(document.activeElement, null, "keydown", { key: "Enter" });
            await triggerEvent(target, null, "keydown", { key: "Escape" });
            assert.containsOnce(
                target,
                ".o_kanban_record:first-child .o_field_many2many_tags_avatar .o_tag",
                "should assign the user"
            );
            assert.containsNone(
                target,
                ".o_kanban_record:first-child .o_field_many2many_tags_avatar .o_popover",
                "should have close the popover"
            );
        }
    );

    QUnit.test(
        "widget many2many_tags_avatar in kanban view missing access rights",
        async function (assert) {
            assert.expect(1);
            await makeView({
                type: "kanban",
                resModel: "turtle",
                serverData,
                arch: `
                <kanban edit="0" create="0">
                    <templates>
                        <t t-name="kanban-box">
                            <div class="oe_kanban_global_click">
                                <field name="display_name"/>
                                <div class="oe_kanban_footer">
                                    <div class="o_kanban_record_bottom">
                                        <div class="oe_kanban_bottom_right">
                                            <field name="partner_ids" widget="many2many_tags_avatar"/>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            });

            assert.containsNone(
                target,
                ".o_kanban_record:first-child .o_field_many2many_tags_avatar .o_quick_assign",
                "should not have the assign icon"
            );
        }
    );

    QUnit.test("widget many2many_tags_avatar", async function (assert) {
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });
        await makeView({
            type: "form",
            resModel: "turtle",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="partner_ids" widget="many2many_tags_avatar"/>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.deepEqual(
            [...target.querySelectorAll("[name='partner_ids'] .o_tag")].map((el) => el.textContent),
            []
        );
        assert.strictEqual(
            target.querySelector("[name='partner_ids'] .o_input_dropdown input").value,
            ""
        );

        await editInput(target, "[name='partner_ids'] .o_input_dropdown input", "first record");
        await triggerEvent(target, "[name='partner_ids'] .o_input_dropdown input", "keydown", {
            key: "Enter",
        });
        assert.deepEqual(
            [...target.querySelectorAll("[name='partner_ids'] .o_tag")].map((el) => el.textContent),
            ["first record"]
        );
        assert.strictEqual(
            target.querySelector("[name='partner_ids'] .o_input_dropdown input").value,
            ""
        );

        await editInput(target, "[name='partner_ids'] .o_input_dropdown input", "abc");
        await triggerEvent(target, "[name='partner_ids'] .o_input_dropdown input", "keydown", {
            key: "Enter",
        });
        assert.deepEqual(
            [...target.querySelectorAll("[name='partner_ids'] .o_tag")].map((el) => el.textContent),
            ["first record", "abc"]
        );
        assert.strictEqual(
            target.querySelector("[name='partner_ids'] .o_input_dropdown input").value,
            ""
        );
    });

    QUnit.test(
        "Many2ManyTagsAvatarField: make sure that the arch context is passed to the form view call",
        async function (assert) {
            serverData.views = {
                "partner,false,form": `<form><field name="display_name"/></form>`,
            };

            patchWithCleanup(browser, {
                setTimeout: (fn) => fn(),
            });

            await makeView({
                type: "list",
                resModel: "turtle",
                serverData,
                arch: `<list editable="top">
                    <field name="partner_ids" widget="many2many_tags_avatar" context="{ 'append_coucou': 'test_value' }"/>
                </list>`,
                mockRPC(route, args) {
                    if (args.method === "onchange" && args.model === "partner") {
                        if (args.kwargs.context.append_coucou === "test_value") {
                            assert.step("onchange with context given");
                        }
                    }
                },
            });

            await click(target.querySelector("div[name=partner_ids]"));
            await editInput(target, `div[name="partner_ids"] input`, "A new partner");
            await clickOpenedDropdownItem(target, "partner_ids", "Create and edit...");

            assert.containsOnce(target, ".modal .o_form_view", "Here we should have opened the modal form view");
            assert.verifySteps(["onchange with context given"]);
        }
    );
});
