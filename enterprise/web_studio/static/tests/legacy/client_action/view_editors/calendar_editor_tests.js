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
                if (args.method === "has_access") {
                    return true;
                }
            },
        });

        await click(
            target.querySelector(
                ".o_web_studio_sidebar .o_web_studio_property_mode .dropdown-toggle"
            )
        );
        const availableModesOptions = target.querySelectorAll(".o-dropdown--menu .dropdown-item");
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
                if (args.method === "has_access") {
                    return true;
                }
            },
        });

        await click(
            target.querySelector(
                ".o_web_studio_sidebar .o_web_studio_property_mode .dropdown-toggle"
            )
        );
        const availableModesOptions = target.querySelectorAll(".o-dropdown--menu .dropdown-item");
        assert.deepEqual(
            Array.from(availableModesOptions).map((el) => el.textContent.trim()),
            ["Day", "Month", "Week", "Year"] // the selectMenu sorts by alphabetical order (it is changeable)
        );
    });

    function getQuickCreateTest(attribute, parsedValue) {
        return async (assert) => {
            const xmlAttribute = attribute !== null ? `quick_create="${attribute}"` : "";

            await createViewEditor({
                serverData,
                type: "calendar",
                resModel: "coucou",
                arch: `
                    <calendar date_start="date_start" ${xmlAttribute}>
                        <field name="display_name"/>
                    </calendar>`,
                mockRPC(route, args) {
                    if (args.method === "has_access") {
                        return true;
                    } else if (route === "/web_studio/edit_view") {
                        assert.step("edit_view");
                        assert.deepEqual(args.operations, [
                            {
                                new_attrs: { quick_create: !parsedValue },
                                type: "attributes",
                                position: "attributes",
                                target: {
                                    tag: "calendar",
                                    attrs: {},
                                    xpath_info: [{ tag: "calendar", indice: 1 }],
                                    isSubviewAttr: true,
                                },
                            },
                        ]);
                    }
                },
            });

            assert.strictEqual(
                target.querySelector(".o_web_studio_property input[name=quick_create]").checked,
                parsedValue
            );

            await click(target, ".o_web_studio_property input[name=quick_create]");

            assert.verifySteps(["edit_view"]);
        };
    }

    QUnit.test("toggling quick_create from true", getQuickCreateTest(true, true));

    QUnit.test("toggling quick_create from false", getQuickCreateTest(false, false));

    QUnit.test("toggling quick_create when attribute is missing", getQuickCreateTest(null, true));
});
