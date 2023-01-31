/** @odoo-module **/

import { click, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

const RED_TEXT = /* html */ `<div class="kek" style="color:red">some text</div>`;

QUnit.module("Fields", ({ beforeEach }) => {
    let serverData;
    let target;

    beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        txt: { string: "txt", type: "html", trim: true },
                        int: { string: "int", type: "integer" },
                    },
                    records: [{ id: 1, txt: RED_TEXT, int: 10 }],
                },
            },
        };
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.module("HtmlField");

    QUnit.debug("listView: html field should take the focus when clicked", async (assert) => {
        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                    <tree editable="top">
                        <field name="txt"/>
                        <field name="int"/>
                    </tree>`,
        });

        await click(target.querySelector(".o_data_row [name='txt']"));
        assert.strictEqual(
            document.activeElement.closest(".o_data_cell").getAttribute("name"),
            "txt"
        );
    });
});
