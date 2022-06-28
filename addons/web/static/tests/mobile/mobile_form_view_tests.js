/** @odoo-module **/

import {
    click,
    clickEdit,
    clickSave,
    editInput,
    getFixture,
    makeDeferred,
    nextTick,
} from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let fixture;
let serverData;

QUnit.module("Mobile Views", ({ beforeEach }) => {
    beforeEach(() => {
        setupViewRegistries();
        fixture = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { type: "char", string: "Display Name" },
                        trululu: { type: "many2one", string: "Trululu", relation: "partner" },
                    },
                    records: [
                        { id: 1, display_name: "first record", trululu: 4 },
                        { id: 2, display_name: "second record", trululu: 1 },
                        { id: 4, display_name: "aaa" },
                    ],
                },
            },
        };
    });

    QUnit.module("FormView");

    QUnit.test(`statusbar buttons are correctly rendered in mobile`, async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <header>
                        <button string="Confirm" />
                        <button string="Do it" />
                    </header>
                    <sheet>
                        <group>
                            <button name="display_name" />
                        </group>
                    </sheet>
                </form>
            `,
        });

        assert.containsOnce(
            fixture,
            ".o_statusbar_buttons .dropdown",
            "statusbar should contain a button 'Action'"
        );
        assert.containsNone(
            fixture,
            ".o_statusbar_buttons .dropdown-menu",
            "statusbar should contain a dropdown"
        );
        assert.containsNone(
            fixture,
            ".o_statusbar_buttons .dropdown-menu:visible",
            "dropdown should be hidden"
        );

        // open the dropdown
        await click(fixture, ".o_statusbar_buttons .dropdown-toggle");
        assert.containsOnce(
            fixture,
            ".o_statusbar_buttons .dropdown-menu:visible",
            "dropdown should be visible"
        );
        assert.containsN(
            fixture,
            ".o_statusbar_buttons .dropdown-menu button",
            2,
            "dropdown should contain 2 buttons"
        );
    });

    QUnit.test(
        `statusbar "Action" button should be displayed only if there are multiple visible buttons`,
        async (assert) => {
            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <header>
                            <button string="Confirm" attrs="{'invisible': [['display_name', '=', 'first record']]}" />
                            <button string="Do it" attrs="{'invisible': [['display_name', '=', 'first record']]}" />
                        </header>
                        <sheet>
                            <group>
                                <field name="display_name" />
                            </group>
                        </sheet>
                    </form>
                `,
            });

            // if all buttons are invisible then there should be no action button
            assert.containsNone(
                fixture,
                ".o_statusbar_buttons > btn-group > .dropdown-toggle",
                "'Action' dropdown is not displayed as there are no visible buttons"
            );

            // change display_name to update buttons modifiers and make it visible
            await clickEdit(fixture);
            await editInput(fixture, ".o_field_widget[name=display_name] input", "test");
            await clickSave(fixture);
            assert.containsOnce(
                fixture,
                ".o_statusbar_buttons .dropdown",
                "statusbar should contain a dropdown"
            );
        }
    );

    QUnit.test(
        `statusbar "Action" button not displayed in edit mode with .oe_read_only button`,
        async (assert) => {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <header>
                            <button string="Share" type="action" class="oe_highlight oe_read_only" />
                            <button string="Email" type="action" class="oe_highlight oe_read_only" />
                        </header>
                        <sheet>
                            <group>
                                <field name="display_name" />
                            </group>
                        </sheet>
                    </form>
                `,
            });

            assert.containsNone(
                fixture,
                ".o_statusbar_buttons .dropdown",
                "dropdown should not be there"
            );

            await clickSave(fixture);
            assert.containsOnce(
                fixture,
                ".o_statusbar_buttons .dropdown",
                "dropdown should not be there"
            );
        }
    );

    QUnit.test(
        `statusbar "Action" button shouldn't be displayed for only one visible button`,
        async (assert) => {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                resId: 1,
                arch: `
                    <form>
                        <header>
                            <button string="Hola" attrs="{'invisible': [['display_name', '=', 'first record']]}" />
                            <button string="Ciao" />
                        </header>
                        <sheet>
                            <group>
                                <field name="display_name" />
                            </group>
                        </sheet>
                    </form>
                `,
            });

            await clickEdit(fixture);

            // There should be a simple statusbar button and no action dropdown
            assert.containsNone(
                fixture,
                ".o_statusbar_buttons .dropdown",
                "should have no 'Action' dropdown"
            );
            assert.containsOnce(
                fixture,
                ".o_statusbar_buttons > button",
                "should have a simple statusbar button"
            );

            // change display_name to update buttons modifiers and make both buttons visible
            await editInput(fixture, ".o_field_widget[name=display_name] input", "test");

            // Now there should an action dropdown, because there are two visible buttons
            assert.containsOnce(
                fixture,
                ".o_statusbar_buttons .dropdown",
                "should have no 'Action' dropdown"
            );
        }
    );

    QUnit.test(
        `statusbar widgets should appear in the statusbar dropdown only if there are multiple items`,
        async (assert) => {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                resId: 2,
                arch: `
                    <form>
                        <header>
                            <widget name="attach_document" string="Attach document" />
                            <button string="Ciao" attrs="{'invisible': [['display_name', '=', 'first record']]}" />
                        </header>
                        <sheet>
                            <group>
                                <field name="display_name" />
                            </group>
                        </sheet>
                    </form>
                `,
            });

            await clickEdit(fixture);
            // Now there should an action dropdown, because there are two visible buttons
            assert.containsOnce(
                fixture,
                ".o_statusbar_buttons .dropdown",
                "should have 'Action' dropdown"
            );

            await click(fixture, ".o_statusbar_buttons .dropdown-toggle");
            assert.containsN(
                fixture,
                ".o_statusbar_buttons .dropdown-menu button",
                2,
                "should have 2 buttons in the dropdown"
            );

            // change display_name to update buttons modifiers and make one button visible
            await editInput(fixture, ".o_field_widget[name=display_name] input", "first record");

            // There should be a simple statusbar button and no action dropdown
            assert.containsNone(
                fixture,
                ".o_statusbar_buttons .dropdown",
                "shouldn't have 'Action' dropdown"
            );
            assert.containsOnce(
                fixture,
                ".o_statusbar_buttons button:visible",
                "should have 1 button visible in the statusbar"
            );
        }
    );

    QUnit.test(
        `statusbar "Action" dropdown should keep its open/close state`,
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <header>
                            <button string="Just more than one" />
                            <button string="Confirm" attrs="{'invisible': [['display_name', '=', '']]}" />
                            <button string="Do it" attrs="{'invisible': [['display_name', '!=', '']]}" />
                        </header>
                        <sheet>
                            <field name="display_name" />
                        </sheet>
                    </form>
                `,
            });

            assert.containsOnce(
                fixture,
                ".o_statusbar_buttons .dropdown",
                "statusbar should contain a dropdown"
            );
            assert.doesNotHaveClass(
                fixture.querySelector(".o_statusbar_buttons .dropdown"),
                "show",
                "dropdown should be closed"
            );

            // open the dropdown
            await click(fixture, ".o_statusbar_buttons .dropdown-toggle");
            assert.hasClass(
                fixture.querySelector(".o_statusbar_buttons .dropdown"),
                "show",
                "dropdown should be opened"
            );

            // change display_name to update buttons' modifiers
            await editInput(fixture, ".o_field_widget[name=display_name] input", "test");
            assert.containsOnce(
                fixture,
                ".o_statusbar_buttons .dropdown",
                "statusbar should contain a dropdown"
            );
            assert.hasClass(
                fixture.querySelector(".o_statusbar_buttons .dropdown"),
                "show",
                "dropdown should still be opened"
            );
        }
    );

    QUnit.test(
        `statusbar "Action" dropdown's open/close state shouldn't be modified after 'onchange'`,
        async function (assert) {
            serverData.models.partner.onchanges = {
                display_name: async () => {},
            };

            const onchangeDef = makeDeferred();

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <header>
                            <button name="create" string="Create Invoice" type="action" />
                            <button name="send" string="Send by Email" type="action" />
                        </header>
                        <sheet>
                            <field name="display_name" />
                        </sheet>
                    </form>
                `,
                mockRPC(route, { method, args: [, , changedField] }) {
                    if (method === "onchange" && changedField === "display_name") {
                        return onchangeDef;
                    }
                },
            });

            assert.containsOnce(
                fixture,
                ".o_statusbar_buttons .dropdown",
                "statusbar should contain a dropdown"
            );
            assert.doesNotHaveClass(
                fixture.querySelector(".o_statusbar_buttons .dropdown"),
                "show",
                "dropdown should be closed"
            );

            await editInput(fixture, ".o_field_widget[name=display_name] input", "before onchange");
            await click(fixture, ".o_statusbar_buttons .dropdown-toggle");
            assert.hasClass(
                fixture.querySelector(".o_statusbar_buttons .dropdown"),
                "show",
                "dropdown should be opened"
            );

            onchangeDef.resolve({ value: { display_name: "after onchange" } });
            await nextTick();
            assert.strictEqual(
                fixture.querySelector(".o_field_widget[name=display_name] input").value,
                "after onchange"
            );
            assert.hasClass(
                fixture.querySelector(".o_statusbar_buttons .dropdown"),
                "show",
                "dropdown should still be opened"
            );
        }
    );
});
