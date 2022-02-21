/** @odoo-module **/

import { click } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
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
        assert.expect(12);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="selection" widget="label_selection" ' +
                " options=\"{'classes': {'normal': 'secondary', 'blocked': 'warning','done': 'success'}}\"/>" +
                "</group>" +
                "</sheet>" +
                "</form>",
            resId: 1,
        });

        assert.containsOnce(
            form.el,
            ".o_field_widget .badge.badge-warning",
            "should have a warning status label since selection is the second, blocked state"
        );
        assert.containsNone(
            form.el,
            ".o_field_widget .badge.badge-secondary",
            "should not have a default status since selection is the second, blocked state"
        );
        assert.containsNone(
            form.el,
            ".o_field_widget .badge.badge-success",
            "should not have a success status since selection is the second, blocked state"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_widget .badge.badge-warning").innerText,
            "Blocked",
            "the label should say 'Blocked' since this is the label value for that state"
        );

        // // switch to edit mode and check the result
        await click(form.el.querySelector(".o_form_button_edit"));
        assert.containsOnce(
            form.el,
            ".o_field_widget .badge.badge-warning",
            "should have a warning status label since selection is the second, blocked state"
        );
        assert.containsNone(
            form.el,
            ".o_field_widget .badge.badge-secondary",
            "should not have a default status since selection is the second, blocked state"
        );
        assert.containsNone(
            form.el,
            ".o_field_widget .badge.badge-success",
            "should not have a success status since selection is the second, blocked state"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_widget .badge.badge-warning").innerText,
            "Blocked",
            "the label should say 'Blocked' since this is the label value for that state"
        );

        // save
        await click(form.el.querySelector(".o_form_button_save"));
        assert.containsOnce(
            form.el,
            ".o_field_widget .badge.badge-warning",
            "should have a warning status label since selection is the second, blocked state"
        );
        assert.containsNone(
            form.el,
            ".o_field_widget .badge.badge-secondary",
            "should not have a default status since selection is the second, blocked state"
        );
        assert.containsNone(
            form.el,
            ".o_field_widget .badge.badge-success",
            "should not have a success status since selection is the second, blocked state"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_widget .badge.badge-warning").innerText,
            "Blocked",
            "the label should say 'Blocked' since this is the label value for that state"
        );
    });

    QUnit.test("LabelSelectionField in editable list view", async function (assert) {
        assert.expect(21);

        const list = await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch:
                '<tree editable="bottom">' +
                '<field name="foo"/>' +
                '<field name="selection" widget="label_selection"' +
                " options=\"{'classes': {'normal': 'secondary', 'blocked': 'warning','done': 'success'}}\"/>" +
                "</tree>",
        });

        assert.strictEqual(
            list.el.querySelectorAll(".o_field_widget .badge:not(:empty)").length,
            3,
            "should have three visible status labels"
        );
        assert.containsOnce(
            list.el,
            ".o_field_widget .badge.badge-warning",
            "should have one warning status label"
        );
        assert.strictEqual(
            list.el.querySelector(".o_field_widget .badge.badge-warning").innerText,
            "Blocked",
            "the warning label should read 'Blocked'"
        );
        assert.containsOnce(
            list.el,
            ".o_field_widget .badge.badge-secondary",
            "should have one default status label"
        );
        assert.strictEqual(
            list.el.querySelector(".o_field_widget .badge.badge-secondary").innerText,
            "Normal",
            "the default label should read 'Normal'"
        );
        assert.containsOnce(
            list.el,
            ".o_field_widget .badge.badge-success",
            "should have one success status label"
        );
        assert.strictEqual(
            list.el.querySelector(".o_field_widget .badge.badge-success").innerText,
            "Done",
            "the success label should read 'Done'"
        );

        // switch to edit mode and check the result
        await click(list.el.querySelector("tbody td:not(.o_list_record_selector)"));
        assert.strictEqual(
            list.el.querySelectorAll(".o_field_widget .badge:not(:empty)").length,
            3,
            "should have three visible status labels"
        );
        assert.containsOnce(
            list.el,
            ".o_field_widget .badge.badge-warning",
            "should have one warning status label"
        );
        assert.strictEqual(
            list.el.querySelector(".o_field_widget .badge.badge-warning").innerText,
            "Blocked",
            "the warning label should read 'Blocked'"
        );
        assert.containsOnce(
            list.el,
            ".o_field_widget .badge.badge-secondary",
            "should have one default status label"
        );
        assert.strictEqual(
            list.el.querySelector(".o_field_widget .badge.badge-secondary").innerText,
            "Normal",
            "the default label should read 'Normal'"
        );
        assert.containsOnce(
            list.el,
            ".o_field_widget .badge.badge-success",
            "should have one success status label"
        );
        assert.strictEqual(
            list.el.querySelector(".o_field_widget .badge.badge-success").innerText,
            "Done",
            "the success label should read 'Done'"
        );

        // save and check the result
        await click(list.el.querySelector(".o_list_button_save"));
        assert.strictEqual(
            list.el.querySelectorAll(".o_field_widget .badge:not(:empty)").length,
            3,
            "should have three visible status labels"
        );
        assert.containsOnce(
            list.el,
            ".o_field_widget .badge.badge-warning",
            "should have one warning status label"
        );
        assert.strictEqual(
            list.el.querySelector(".o_field_widget .badge.badge-warning").innerText,
            "Blocked",
            "the warning label should read 'Blocked'"
        );
        assert.containsOnce(
            list.el,
            ".o_field_widget .badge.badge-secondary",
            "should have one default status label"
        );
        assert.strictEqual(
            list.el.querySelector(".o_field_widget .badge.badge-secondary").innerText,
            "Normal",
            "the default label should read 'Normal'"
        );
        assert.containsOnce(
            list.el,
            ".o_field_widget .badge.badge-success",
            "should have one success status label"
        );
        assert.strictEqual(
            list.el.querySelector(".o_field_widget .badge.badge-success").innerText,
            "Done",
            "the success label should read 'Done'"
        );
    });
});
