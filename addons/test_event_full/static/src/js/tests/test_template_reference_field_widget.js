/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { click, getFixture, editSelect, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let target;
let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();

        serverData = {
            models: {
                mail: {
                    fields: {
                        template_ref: {
                            string: "Template",
                            type: "reference",
                            selection: [
                                ["mail.template", "Mail Template"],
                                ["sms.template", "SMS Template"],
                                ["some.template", "Some Template"],
                            ],
                        },
                    },
                    records: [
                        {
                            id: 1,
                            template_ref: "mail.template,1",
                        },
                        {
                            id: 2,
                            template_ref: "sms.template,1",
                        },
                        {
                            id: 3,
                            template_ref: "some.template,1",
                        },
                    ],
                },
                "mail.template": {
                    fields: {
                        name: {
                            string: "Name",
                            type: "text",
                        },
                    },
                    records: [{ id: 1, name: "Mail Template 1" }],
                },
                "sms.template": {
                    fields: {
                        name: {
                            string: "Name",
                            type: "text",
                        },
                    },
                    records: [{ id: 1, name: "SMS template 1" }],
                },
                "some.template": {
                    fields: {
                        name: {
                            string: "Name",
                            type: "text",
                        },
                    },
                    records: [{ id: 1, name: "Some Template 1" }],
                },
                "ir.model": {
                    fields: {
                        model: { string: "Model", type: "char" },
                    },
                    records: [
                        {
                            id: 17,
                            name: "Partner",
                            model: "partner",
                        },
                        {
                            id: 20,
                            name: "Product",
                            model: "product",
                        },
                        {
                            id: 21,
                            name: "Partner Type",
                            model: "partner_type",
                        },
                    ],
                    onchanges: {},
                },
            },
        };

        setupViewRegistries();

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });
    });

    QUnit.test("Reference field displays right icons", async function (assert) {
        assert.expect(12);
        await makeView({
            type: "list",
            resModel: "mail",
            serverData,
            arch: `
            <tree editable="top">
                <field name="template_ref" widget="event_mail_template_reference_field"/>
            </tree>`,
        });

        assert.containsN(target, ".o_field_cell", 3);
        assert.containsN(target, ".o_field_cell.o_event_mail_template_reference_field_cell", 3);
        let cells = [...target.querySelectorAll(".o_field_cell")];
        assert.containsOnce(cells[0], ".fa-envelope");
        assert.containsOnce(cells[1], ".fa-mobile");
        assert.containsNone(cells[2], ".fa-envelope");
        assert.containsNone(cells[2], ".fa-mobile");

        // select a sms.template instead of mail.template

        await click(cells[0]);
        // cells may change when clicking another, update the list
        cells = [...target.querySelectorAll(".o_field_cell")];
        await editSelect(cells[0], "select", "sms.template");
        await click(cells[0], ".o_field_many2one_selection input");
        await click(cells[0].querySelector(".o-autocomplete--dropdown-item"));
        await click(target);
        cells = [...target.querySelectorAll(".o_field_cell")];

        assert.containsOnce(cells[0], ".fa-mobile");
        assert.containsNone(cells[0], ".fa-envelope");

        // select a some other model to check it has no icon

        await click(cells[0]);
        cells = [...target.querySelectorAll(".o_field_cell")];
        await editSelect(cells[0], "select", "some.template");
        await click(cells[0], ".o_field_many2one_selection input");
        await click(cells[0].querySelector(".o-autocomplete--dropdown-item"));
        await click(target);
        cells = [...target.querySelectorAll(".o_field_cell")];

        assert.containsNone(cells[0], ".fa-mobile");
        assert.containsNone(cells[0], ".fa-envelope");

        // select no record for the model

        // reset to click on cell 1 for consistency
        await click(cells[0]);
        cells = [...target.querySelectorAll(".o_field_cell")];
        await click(cells[1]);
        cells = [...target.querySelectorAll(".o_field_cell")];
        await editSelect(cells[1], "select", "mail.template");
        await click(target);
        cells = [...target.querySelectorAll(".o_field_cell")];

        assert.containsNone(cells[1], ".fa-mobile");
        assert.containsNone(cells[1], ".fa-envelope");
    });
});
