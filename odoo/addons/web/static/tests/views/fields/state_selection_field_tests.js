/** @odoo-module **/

import { click, getFixture, nextTick, triggerHotkey } from "@web/../tests/helpers/utils";
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
                        foo: {
                            string: "Foo",
                            type: "char",
                        },
                        sequence: { type: "integer", string: "Sequence", searchable: true },
                        selection: {
                            string: "Selection",
                            type: "selection",
                            selection: [
                                ["normal", "Normal"],
                                ["blocked", "Blocked"],
                                ["done", "Done"],
                            ],
                        },
                    },
                    records: [
                        {
                            id: 1,
                            foo: "yop",
                            selection: "blocked",
                        },
                        {
                            id: 2,
                            foo: "blip",
                            selection: "normal",
                        },
                        {
                            id: 4,
                            foo: "abc",
                            selection: "done",
                        },
                        { id: 3, foo: "gnap" },
                        { id: 5, foo: "blop" },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("StateSelectionField");

    QUnit.test("StateSelectionField in form view", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="selection" widget="state_selection"/>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(
            target,
            ".o_field_widget.o_field_state_selection span.o_status.o_status_red",
            "should have one red status since selection is the second, blocked state"
        );
        assert.containsNone(
            target,
            ".o_field_widget.o_field_state_selection span.o_status.o_status_green",
            "should not have one green status since selection is the second, blocked state"
        );
        assert.containsNone(target, ".o_content .dropdown-menu", "there should not be a dropdown");

        // Click on the status button to make the dropdown appear
        await click(target, ".o_field_widget.o_field_state_selection .o_status");
        assert.containsOnce(
            document.body,
            ".o_content .dropdown-menu",
            "there should be a dropdown"
        );
        assert.containsN(
            target,
            ".o_content .dropdown-menu .dropdown-item",
            3,
            "there should be three options in the dropdown"
        );
        assert.hasClass(
            target.querySelector(".dropdown-menu .dropdown-item:nth-child(2)"),
            "active",
            "current value has a checkmark"
        );

        // Click on the first option, "Normal"
        await click(target.querySelector(".o_content .dropdown-menu .dropdown-item"));
        assert.containsNone(
            target,
            ".o_content .dropdown-menu",
            "there should not be a dropdown anymore"
        );
        assert.containsNone(
            target,
            ".o_field_widget.o_field_state_selection span.o_status.o_status_red",
            "should not have one red status since selection is the first, normal state"
        );
        assert.containsNone(
            target,
            ".o_field_widget.o_field_state_selection span.o_status.o_status_green",
            "should not have one green status since selection is the first, normal state"
        );
        assert.containsOnce(
            target,
            ".o_field_widget.o_field_state_selection span.o_status",
            "should have one grey status since selection is the first, normal state"
        );

        assert.containsNone(
            target,
            ".o_content .dropdown-menu",
            "there should still not be a dropdown"
        );
        assert.containsNone(
            target,
            ".o_field_widget.o_field_state_selection span.o_status.o_status_red",
            "should still not have one red status since selection is the first, normal state"
        );
        assert.containsNone(
            target,
            ".o_field_widget.o_field_state_selection span.o_status.o_status_green",
            "should still not have one green status since selection is the first, normal state"
        );
        assert.containsOnce(
            target,
            ".o_field_widget.o_field_state_selection span.o_status",
            "should still have one grey status since selection is the first, normal state"
        );

        // Click on the status button to make the dropdown appear
        await click(target, ".o_field_widget.o_field_state_selection .o_status");
        assert.containsOnce(target, ".o_content .dropdown-menu", "there should be a dropdown");
        assert.containsN(
            target,
            ".dropdown-menu .dropdown-item",
            3,
            "there should be three options in the dropdown"
        );

        // Click on the last option, "Done"
        await click(target, ".o_content .dropdown-menu .dropdown-item:last-child");
        assert.containsNone(
            target,
            ".o_content .dropdown-menu",
            "there should not be a dropdown anymore"
        );
        assert.containsNone(
            target,
            ".o_field_widget.o_field_state_selection span.o_status.o_status_red",
            "should not have one red status since selection is the third, done state"
        );
        assert.containsOnce(
            target,
            ".o_field_widget.o_field_state_selection span.o_status.o_status_green",
            "should have one green status since selection is the third, done state"
        );

        // save
        await click(target.querySelector(".o_form_button_save"));
        assert.containsNone(
            target,
            ".o_content .dropdown-menu",
            "there should still not be a dropdown anymore"
        );
        assert.containsNone(
            target,
            ".o_field_widget.o_field_state_selection span.o_status.o_status_red",
            "should still not have one red status since selection is the third, done state"
        );
        assert.containsOnce(
            target,
            ".o_field_widget.o_field_state_selection span.o_status.o_status_green",
            "should still have one green status since selection is the third, done state"
        );
    });

    QUnit.test("StateSelectionField with readonly modifier", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="selection" widget="state_selection" readonly="1"/></form>',
            resId: 1,
        });

        assert.hasClass(target.querySelector(".o_field_state_selection"), "o_readonly_modifier");
        assert.isNotVisible(target.querySelector(".dropdown-menu"));
        await click(target, ".o_field_state_selection span.o_status");
        assert.isNotVisible(target.querySelector(".dropdown-menu"));
    });

    QUnit.test("StateSelectionField for form view with hide_label option", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="selection" widget="state_selection" options="{'hide_label': False}"/>
                </form>
            `,
            resId: 1,
        });
        assert.containsOnce(target, ".o_status_label");
    });

    QUnit.test("StateSelectionField for list view with hide_label option", async function (assert) {
        Object.assign(serverData.models.partner.fields, {
            graph_type: {
                string: "Graph Type",
                type: "selection",
                selection: [
                    ["line", "Line"],
                    ["bar", "Bar"],
                ],
            },
        });
        serverData.models.partner.records[0].graph_type = "bar";
        serverData.models.partner.records[1].graph_type = "line";

        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree>
                    <field name="graph_type" widget="state_selection" options="{'hide_label': True}"/>
                    <field name="selection" widget="state_selection" options="{'hide_label': False}"/>
                </tree>`,
        });

        assert.containsN(
            target,
            ".o_state_selection_cell .o_field_state_selection span.o_status",
            10,
            "should have ten status selection widgets"
        );
        const selection = Array.from(
            target.querySelectorAll(
                ".o_state_selection_cell .o_field_state_selection[name=selection] span.o_status_label"
            )
        );
        assert.strictEqual(selection.length, 5, "should have five label on selection widgets");
        assert.strictEqual(
            selection.filter((el) => el.textContent === "Done").length,
            1,
            "should have one Done status label"
        );
        assert.strictEqual(
            selection.filter((el) => el.textContent === "Normal").length,
            3,
            "should have three Normal status label"
        );
        assert.containsN(
            target,
            ".o_state_selection_cell .o_field_state_selection[name=graph_type] span.o_status",
            5,
            "should have five status selection widgets"
        );
        assert.containsNone(
            target,
            ".o_state_selection_cell .o_field_state_selection[name=graph_type] span.o_status_label",
            "should not have status label in selection widgets"
        );
    });

    QUnit.test("StateSelectionField in editable list view", async function (assert) {
        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="foo"/>
                    <field name="selection" widget="state_selection"/>
                </tree>`,
        });

        assert.containsN(
            target,
            ".o_state_selection_cell .o_field_state_selection span.o_status",
            5,
            "should have five status selection widgets"
        );
        assert.containsOnce(
            target,
            ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_red",
            "should have one red status"
        );
        assert.containsOnce(
            target,
            ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_green",
            "should have one green status"
        );
        assert.containsNone(target, ".o_content .dropdown-menu", "there should not be a dropdown");

        // Click on the status button to make the dropdown appear
        let cell = target.querySelector("tbody td.o_state_selection_cell");
        await click(
            target.querySelector(".o_state_selection_cell .o_field_state_selection span.o_status")
        );
        assert.doesNotHaveClass(
            cell.parentElement,
            "o_selected_row",
            "should not be in edit mode since we clicked on the state selection widget"
        );
        assert.containsOnce(target, ".o_content .dropdown-menu", "there should be a dropdown");
        assert.containsN(
            target,
            ".o_content .dropdown-menu .dropdown-item",
            3,
            "there should be three options in the dropdown"
        );

        // Click on the first option, "Normal"
        await click(target.querySelector(".o_content .dropdown-menu .dropdown-item"));
        assert.containsN(
            target,
            ".o_state_selection_cell .o_field_state_selection span.o_status",
            5,
            "should still have five status selection widgets"
        );
        assert.containsNone(
            target,
            ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_red",
            "should now have no red status"
        );
        assert.containsOnce(
            target,
            ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_green",
            "should still have one green status"
        );
        assert.containsNone(target, ".o_content .dropdown-menu", "there should not be a dropdown");
        assert.containsNone(target, "tr.o_selected_row", "should not be in edit mode");

        // switch to edit mode and check the result
        cell = target.querySelector("tbody td.o_state_selection_cell");
        await click(cell);
        assert.hasClass(cell.parentElement, "o_selected_row", "should now be in edit mode");
        assert.containsN(
            target,
            ".o_state_selection_cell .o_field_state_selection span.o_status",
            5,
            "should still have five status selection widgets"
        );
        assert.containsNone(
            target,
            ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_red",
            "should now have no red status"
        );
        assert.containsOnce(
            target,
            ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_green",
            "should still have one green status"
        );
        assert.containsNone(target, ".o_content .dropdown-menu", "there should not be a dropdown");

        // Click on the status button to make the dropdown appear
        await click(
            target.querySelector(".o_state_selection_cell .o_field_state_selection span.o_status")
        );
        assert.containsOnce(target, ".o_content .dropdown-menu", "there should be a dropdown");
        assert.containsN(
            target,
            ".o_content .dropdown-menu .dropdown-item",
            3,
            "there should be three options in the dropdown"
        );

        // Click on another row
        const lastCell = target.querySelectorAll("tbody td.o_state_selection_cell")[4];
        await click(lastCell);
        assert.containsNone(
            target,
            ".o_content .dropdown-menu",
            "there should not be a dropdown anymore"
        );
        const firstCell = target.querySelector("tbody td.o_state_selection_cell");
        assert.doesNotHaveClass(
            firstCell.parentElement,
            "o_selected_row",
            "first row should not be in edit mode anymore"
        );
        assert.hasClass(
            lastCell.parentElement,
            "o_selected_row",
            "last row should be in edit mode"
        );

        // Click on the fourth status button to make the dropdown appear
        await click(
            target.querySelectorAll(
                ".o_state_selection_cell .o_field_state_selection span.o_status"
            )[3]
        );
        assert.containsOnce(target, ".o_content .dropdown-menu", "there should be a dropdown");
        assert.containsN(
            target,
            ".o_content .dropdown-menu .dropdown-item",
            3,
            "there should be three options in the dropdown"
        );

        // Click on the last option, "Done"
        await click(target, ".o_content .dropdown-menu .dropdown-item:last-child");
        assert.containsNone(
            target,
            ".o_content .dropdown-menu",
            "there should not be a dropdown anymore"
        );
        assert.containsN(
            target,
            ".o_state_selection_cell .o_field_state_selection span.o_status",
            5,
            "should still have five status selection widgets"
        );
        assert.containsNone(
            target,
            ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_red",
            "should still have no red status"
        );
        assert.containsN(
            target,
            ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_green",
            2,
            "should now have two green status"
        );
        assert.containsNone(target, ".o_content .dropdown-menu", "there should not be a dropdown");

        // save
        await click(
            target.querySelector(
                ".o_control_panel_main_buttons .d-none.d-xl-inline-flex .o_list_button_save"
            )
        );
        assert.containsN(
            target,
            ".o_state_selection_cell .o_field_state_selection span.o_status",
            5,
            "should have five status selection widgets"
        );
        assert.containsNone(
            target,
            ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_red",
            "should have no red status"
        );
        assert.containsN(
            target,
            ".o_state_selection_cell .o_field_state_selection span.o_status.o_status_green",
            2,
            "should have two green status"
        );
        assert.containsNone(target, ".o_content .dropdown-menu", "there should not be a dropdown");
    });

    QUnit.test(
        'StateSelectionField edited by the smart actions "Set kanban state as <state name>"',
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="selection" widget="state_selection"/>
                    </form>`,
                resId: 1,
            });

            assert.containsOnce(target, ".o_status_red");

            triggerHotkey("control+k");
            await nextTick();
            var commandTexts = [...target.querySelectorAll(".o_command")].map(
                (el) => el.textContent
            );
            assert.ok(commandTexts.includes("Set kanban state as NormalALT + D"));
            const idx = commandTexts.indexOf("Set kanban state as DoneALT + G");
            assert.ok(idx >= 0);

            await click([...target.querySelectorAll(".o_command")][idx]);
            await nextTick();
            assert.containsOnce(target, ".o_status_green");

            triggerHotkey("control+k");
            await nextTick();
            commandTexts = [...target.querySelectorAll(".o_command")].map((el) => el.textContent);
            assert.ok(commandTexts.includes("Set kanban state as NormalALT + D"));
            assert.ok(commandTexts.includes("Set kanban state as BlockedALT + F"));
            assert.notOk(commandTexts.includes("Set kanban state as DoneALT + G"));
        }
    );

    QUnit.test("StateSelectionField uses legend_* fields", async function (assert) {
        serverData.models.partner.fields.legend_normal = { type: "char" };
        serverData.models.partner.fields.legend_blocked = { type: "char" };
        serverData.models.partner.fields.legend_done = { type: "char" };
        serverData.models.partner.records[0].legend_normal = "Custom normal";
        serverData.models.partner.records[0].legend_blocked = "Custom blocked";
        serverData.models.partner.records[0].legend_done = "Custom done";

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="legend_normal" invisible="1" />
                            <field name="legend_blocked" invisible="1" />
                            <field name="legend_done" invisible="1" />
                            <field name="selection" widget="state_selection"/>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });

        await click(target, ".o_status");
        let dropdownItemTexts = [
            ...target.querySelectorAll(".o_field_state_selection .dropdown-item"),
        ].map((el) => el.textContent);
        assert.deepEqual(dropdownItemTexts, ["Custom normal", "Custom blocked", "Custom done"]);

        await click(target.querySelector(".dropdown-item .o_status"));
        await click(target, ".o_status");
        dropdownItemTexts = [
            ...target.querySelectorAll(".o_field_state_selection .dropdown-item"),
        ].map((el) => el.textContent);
        assert.deepEqual(dropdownItemTexts, ["Custom normal", "Custom blocked", "Custom done"]);
    });

    QUnit.test("works when required in a readonly view ", async function (assert) {
        serverData.models.partner.records[0].selection = "normal";
        serverData.models.partner.records = [serverData.models.partner.records[0]];
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="selection" widget="state_selection" required="1"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            mockRPC: (route, args, performRPC) => {
                if (route === "/web/dataset/call_kw/partner/web_save") {
                    assert.step("web_save");
                }
                return performRPC(route, args);
            },
        });
        assert.containsNone(target, ".o_status_label");

        await click(target, ".o_field_state_selection button");
        const doneItem = target.querySelectorAll(".dropdown-item")[2]; // item "done";
        await click(doneItem);

        assert.verifySteps(["web_save"]);
        assert.hasClass(target.querySelector(".o_field_state_selection span"), "o_status_green");
    });

    QUnit.test(
        "StateSelectionField - auto save record when field toggled",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="selection" widget="state_selection"/>
                            </group>
                        </sheet>
                    </form>`,
                resId: 1,
                mockRPC(_route, { method }) {
                    if (method === "web_save") {
                        assert.step("web_save");
                    }
                },
            });

            await click(target, ".o_field_widget.o_field_state_selection .o_status");
            await click(target, ".dropdown-menu .dropdown-item:last-child");
            assert.verifySteps(["web_save"]);
        }
    );

    QUnit.test(
        "StateSelectionField -  prevent auto save with autosave option",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="selection" widget="state_selection" options="{'autosave': False}"/>
                            </group>
                        </sheet>
                    </form>`,
                resId: 1,
                mockRPC(_route, { method }) {
                    if (method === "write") {
                        assert.step("write");
                    }
                },
            });

            await click(target, ".o_field_widget.o_field_state_selection .o_status");
            await click(target, ".dropdown-menu .dropdown-item:last-child");
            assert.verifySteps([]);
        }
    );

    QUnit.test(
        "StateSelectionField - hotkey handling when there are more than 3 options available",
        async function (assert) {
            serverData.models.partner.fields.selection.selection.push(
                ["martin", "Martin"],
                ["martine", "Martine"]
            );
            serverData.models.partner.records[0].selection = null;

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="selection" widget="state_selection" options="{'autosave': False}"/>
                            </group>
                        </sheet>
                    </form>`,
                resId: 1,
            });

            await click(target, ".o_field_widget.o_field_state_selection .o_status");
            assert.containsN(
                target,
                ".dropdown-menu .dropdown-item",
                5,
                "Five choices are displayed"
            );
            triggerHotkey("control+k");

            await nextTick();
            assert.strictEqual(
                target.querySelector(".o_command#o_command_2").textContent,
                "Set kanban state as DoneALT + G",
                "hotkey and command are present"
            );
            assert.strictEqual(
                target.querySelector(".o_command#o_command_4").textContent,
                "Set kanban state as Martine",
                "no hotkey is present, but the command exists"
            );

            await click(target.querySelector(".o_command#o_command_2"));
            assert.hasClass(
                target.querySelector(".o_status"),
                "o_status_green",
                "green color and Done state have been set"
            );
        }
    );
});
