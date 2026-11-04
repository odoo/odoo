/** @odoo-module alias=@web/../tests/mobile/views/fields/statusbar_field_tests default=false */

import { click, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registerCleanup } from "@web/../tests/helpers/cleanup";

let fixture;
let serverData;

QUnit.module("Mobile Fields", ({ beforeEach }) => {
    beforeEach(() => {
        setupViewRegistries();
        fixture = getFixture();
        fixture.setAttribute("style", "width:100vw; height:100vh;");
        registerCleanup(() => fixture.removeAttribute("style"));
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        trululu: { string: "Trululu", type: "many2one", relation: "partner" },
                    },
                    records: [
                        { id: 1, display_name: "first record", trululu: 4 },
                        { id: 2, display_name: "second record", trululu: 1 },
                        { id: 3, display_name: "third record" },
                        { id: 4, display_name: "aaa" },
                    ],
                },
            },
        };
    });

    QUnit.module("StatusBarField");

    QUnit.test("statusbar is rendered correctly on small devices", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <header>
                        <field name="trululu" widget="statusbar" />
                    </header>
                    <field name="display_name" />
                </form>
            `,
        });

        assert.containsN(fixture, ".o_statusbar_status .o_arrow_button:visible", 4);
        assert.containsOnce(fixture, ".o_statusbar_status .o_arrow_button.dropdown-toggle:visible");
        assert.containsOnce(fixture, ".o_statusbar_status .o_arrow_button.o_arrow_button_current");
        assert.containsNone(fixture, ".o-dropdown--menu", "dropdown should be hidden");
        assert.strictEqual(
            fixture.querySelector(".o_statusbar_status button.dropdown-toggle").textContent.trim(),
            "..."
        );

        // open the dropdown
        await click(fixture, ".o_statusbar_status .dropdown-toggle.o_last");

        assert.containsOnce(fixture, ".o-dropdown--menu", "dropdown should be visible");
        assert.containsOnce(fixture, ".o-dropdown--menu .dropdown-item.disabled");
    });

    QUnit.test("statusbar with no status on extra small screens", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 4,
            serverData,
            arch: `
                <form>
                    <header>
                        <field name="trululu" widget="statusbar" />
                    </header>
                </form>
            `,
        });

        assert.doesNotHaveClass(
            fixture.querySelector(".o_field_statusbar"),
            "o_field_empty",
            "statusbar widget should have class o_field_empty in edit"
        );
        assert.containsOnce(fixture, ".o_statusbar_status button.dropdown-toggle:visible:disabled");
        assert.strictEqual(
            $(".o_statusbar_status button.dropdown-toggle:visible:disabled").text().trim(),
            "..."
        );

    });

    QUnit.test("clickable statusbar widget on mobile view", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <header>
                        <field name="trululu" widget="statusbar" options="{'clickable': '1'}" />
                    </header>
                </form>
            `,
        });

        // Open dropdown
        await click($(".o_statusbar_status .dropdown-toggle:visible")[0]);

        assert.containsOnce(fixture, ".o-dropdown--menu .dropdown-item");

        await click(fixture, ".o-dropdown--menu .dropdown-item");

        assert.strictEqual($(".o_arrow_button_current").text(), "first record");
        assert.containsN(fixture, ".o_statusbar_status .o_arrow_button:visible", 3);
        assert.containsOnce(fixture, ".o_statusbar_status .dropdown-toggle:visible");

        // Open second dropdown
        await click($(".o_statusbar_status .dropdown-toggle:visible")[0]);

        assert.containsN(fixture, ".o-dropdown--menu .dropdown-item", 2);
    });
});
