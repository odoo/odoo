/** @odoo-module **/

import { click, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let fixture;
let serverData;

QUnit.module("Mobile Fields", ({ beforeEach }) => {
    beforeEach(() => {
        setupViewRegistries();
        fixture = getFixture();
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
                        { id: 4, display_name: "aaa" },
                    ],
                },
            },
        };
    });

    QUnit.module("StatusBarField");

    QUnit.test("statusbar is rendered correclty on small devices", async (assert) => {
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

        assert.containsOnce(
            fixture,
            ".o_statusbar_status > button",
            "should have only one visible status in mobile, the active one"
        );
        assert.containsOnce(
            fixture,
            ".o_statusbar_status .dropdown",
            "should have a dropdown containing all status"
        );
        assert.containsNone(
            fixture,
            ".o_statusbar_status .dropdown-menu",
            "dropdown should be hidden"
        );
        assert.strictEqual(
            fixture.querySelector(".o_statusbar_status button.dropdown-toggle").textContent.trim(),
            "aaa",
            "statusbar button should display current field value"
        );

        // open the dropdown
        await click(fixture, ".o_statusbar_status > button");
        assert.containsOnce(
            fixture,
            ".o_statusbar_status .dropdown-menu",
            "dropdown should be visible"
        );
        assert.containsN(
            fixture,
            ".o_statusbar_status .dropdown-menu .btn",
            3,
            "should have 3 status"
        );
        assert.containsN(
            fixture,
            ".o_statusbar_status .btn.disabled",
            3,
            "all status should be disabled"
        );
        assert.hasClass(
            fixture.querySelector(".o_statusbar_status .btn:nth-child(3)"),
            "btn-primary",
            "active status should be btn-primary"
        );
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
        assert.containsOnce(
            fixture,
            ".o_statusbar_status button.dropdown-toggle",
            "statusbar widget should have a button"
        );
        assert.strictEqual(
            fixture.querySelector(".o_statusbar_status button.dropdown-toggle").textContent.trim(),
            "",
            "statusbar button shouldn't have text for null field value"
        );

        await click(fixture, ".o_statusbar_status button.dropdown-toggle");
        assert.containsOnce(
            fixture,
            ".o_statusbar_status .dropdown-menu",
            "statusbar widget should have a dropdown menu"
        );
        assert.containsN(
            fixture,
            ".o_statusbar_status .dropdown-menu .btn",
            3,
            "statusbar widget dropdown menu should have 3 buttons"
        );
        assert.strictEqual(
            fixture
                .querySelectorAll(".o_statusbar_status .dropdown-menu .btn")[0]
                .textContent.trim(),
            "first record",
            "statusbar widget dropdown first button should display the first record display_name"
        );
        assert.strictEqual(
            fixture
                .querySelectorAll(".o_statusbar_status .dropdown-menu .btn")[1]
                .textContent.trim(),
            "second record",
            "statusbar widget dropdown second button should display the second record display_name"
        );
        assert.strictEqual(
            fixture
                .querySelectorAll(".o_statusbar_status .dropdown-menu .btn")[2]
                .textContent.trim(),
            "aaa",
            "statusbar widget dropdown third button should display the third record display_name"
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

        await click(fixture, ".o_statusbar_status .dropdown-toggle");
        assert.hasClass(
            fixture.querySelector(".o_statusbar_status .dropdown-menu .btn:nth-child(3)"),
            "btn-primary"
        );
        assert.hasClass(
            fixture.querySelector(".o_statusbar_status .dropdown-menu .btn:nth-child(3)"),
            "disabled"
        );

        assert.containsN(
            fixture,
            ".o_statusbar_status .btn-secondary:not(.dropdown-toggle):not(.disabled)",
            2,
            "other status should be btn-secondary and not disabled"
        );

        await click(
            fixture.querySelector(
                ".o_statusbar_status .btn-secondary:not(.dropdown-toggle):not(.disabled)"
            )
        );

        await click(fixture, ".o_statusbar_status .dropdown-toggle");
        assert.hasClass(
            fixture.querySelector(".o_statusbar_status .dropdown-menu .btn:nth-child(1)"),
            "btn-primary"
        );
        assert.hasClass(
            fixture.querySelector(".o_statusbar_status .dropdown-menu .btn:nth-child(1)"),
            "disabled"
        );
    });
});
