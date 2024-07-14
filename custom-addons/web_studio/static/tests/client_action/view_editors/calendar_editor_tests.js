/** @odoo-module */
import { click, getFixture } from "@web/../tests/helpers/utils";
import { createViewEditor, registerViewEditorDependencies } from "./view_editor_tests_utils";

QUnit.module("View Editors", (hooks) => {
    QUnit.module("Calendar");

    let target, serverData;

    hooks.beforeEach(() => {
        registerViewEditorDependencies();
        target = getFixture();
        serverData = {
            models: {
                coucou: {
                    fields: {
                        date_start: { type: "date", string: "Date start" },
                    },
                    records: [],
                },
            },
        };
    });

    QUnit.test("constrain available periods to the scale attribute", async function (assert) {
        await createViewEditor({
            serverData,
            type: "calendar",
            resModel: "coucou",
            arch: `
            <calendar scales="month,year" date_start="date_start">
                <field name="display_name" />
            </calendar>`,
            mockRPC(route, args) {
                if (args.method === "check_access_rights") {
                    return true;
                }
            },
        });

        await click(
            target.querySelector(
                ".o_web_studio_sidebar .o_web_studio_property_mode .dropdown-toggle"
            )
        );
        const availableModesOptions = target.querySelectorAll(
            ".o_web_studio_sidebar .o_web_studio_property_mode .o-dropdown--menu .dropdown-item"
        );
        assert.deepEqual(
            Array.from(availableModesOptions).map((el) => el.textContent.trim()),
            ["Month", "Year"]
        );
    });

    QUnit.test("available periods without scale attribute", async function (assert) {
        await createViewEditor({
            serverData,
            type: "calendar",
            resModel: "coucou",
            arch: `
            <calendar date_start="date_start">
                <field name="display_name" />
            </calendar>`,
            mockRPC(route, args) {
                if (args.method === "check_access_rights") {
                    return true;
                }
            },
        });

        await click(
            target.querySelector(
                ".o_web_studio_sidebar .o_web_studio_property_mode .dropdown-toggle"
            )
        );
        const availableModesOptions = target.querySelectorAll(
            ".o_web_studio_sidebar .o_web_studio_property_mode .o-dropdown--menu .dropdown-item"
        );
        assert.deepEqual(
            Array.from(availableModesOptions).map((el) => el.textContent.trim()),
            ["Day", "Month", "Week", "Year"] // the selectMenu sorts by alphabetical order (it is changeable)
        );
    });
});
