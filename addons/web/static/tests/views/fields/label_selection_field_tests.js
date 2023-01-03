/** @odoo-module **/

import { click, getFixture } from "@web/../tests/helpers/utils";
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
                            default: "My little Foo Value",
                            searchable: true,
                            trim: true,
                        },
                        selection: {
                            string: "Selection",
                            type: "selection",
                            searchable: true,
                            selection: [
                                ["normal", "Normal"],
                                ["blocked", "Blocked"],
                                ["done", "Done"],
                            ],
                        },
                    },
                    records: [
                        {
                            foo: "yop",
                            selection: "blocked",
                        },
                        {
                            foo: "blip",
                            selection: "normal",
                        },
                        {
                            foo: "abc",
                            selection: "done",
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("LabelSelectionField");

    QUnit.test("LabelSelectionField in form view", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="selection" widget="label_selection"
                            options="{'classes': {'normal': 'secondary', 'blocked': 'warning','done': 'success'}}"/>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(
            target,
            ".o_field_widget .badge.text-bg-warning",
            "should have a warning status label since selection is the second, blocked state"
        );
        assert.containsNone(
            target,
            ".o_field_widget .badge.text-bg-secondary",
            "should not have a default status since selection is the second, blocked state"
        );
        assert.containsNone(
            target,
            ".o_field_widget .badge.text-bg-success",
            "should not have a success status since selection is the second, blocked state"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget .badge.text-bg-warning").textContent,
            "Blocked",
            "the label should say 'Blocked' since this is the label value for that state"
        );
    });

    QUnit.test("LabelSelectionField in editable list view", async function (assert) {
        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="foo"/>
                    <field name="selection" widget="label_selection"
                    options="{'classes': {'normal': 'secondary', 'blocked': 'warning','done': 'success'}}"/>
                </tree>`,
        });

        assert.strictEqual(
            target.querySelectorAll(".o_field_widget .badge:not(:empty)").length,
            3,
            "should have three visible status labels"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .badge.text-bg-warning",
            "should have one warning status label"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget .badge.text-bg-warning").textContent,
            "Blocked",
            "the warning label should read 'Blocked'"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .badge.text-bg-secondary",
            "should have one default status label"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget .badge.text-bg-secondary").textContent,
            "Normal",
            "the default label should read 'Normal'"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .badge.text-bg-success",
            "should have one success status label"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget .badge.text-bg-success").textContent,
            "Done",
            "the success label should read 'Done'"
        );

        // switch to edit mode and check the result
        await click(target.querySelector("tbody td:not(.o_list_record_selector)"));
        assert.strictEqual(
            target.querySelectorAll(".o_field_widget .badge:not(:empty)").length,
            3,
            "should have three visible status labels"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .badge.text-bg-warning",
            "should have one warning status label"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget .badge.text-bg-warning").textContent,
            "Blocked",
            "the warning label should read 'Blocked'"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .badge.text-bg-secondary",
            "should have one default status label"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget .badge.text-bg-secondary").textContent,
            "Normal",
            "the default label should read 'Normal'"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .badge.text-bg-success",
            "should have one success status label"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget .badge.text-bg-success").textContent,
            "Done",
            "the success label should read 'Done'"
        );

        // save and check the result
        await click(target.querySelector(".o_list_button_save"));
        assert.strictEqual(
            target.querySelectorAll(".o_field_widget .badge:not(:empty)").length,
            3,
            "should have three visible status labels"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .badge.text-bg-warning",
            "should have one warning status label"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget .badge.text-bg-warning").textContent,
            "Blocked",
            "the warning label should read 'Blocked'"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .badge.text-bg-secondary",
            "should have one default status label"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget .badge.text-bg-secondary").textContent,
            "Normal",
            "the default label should read 'Normal'"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .badge.text-bg-success",
            "should have one success status label"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget .badge.text-bg-success").textContent,
            "Done",
            "the success label should read 'Done'"
        );
    });
});
