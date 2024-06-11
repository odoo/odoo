/** @odoo-module **/
import { editSelect, getFixture } from "@web/../tests/helpers/utils";
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
                        fonts: {
                            type: "selection",
                            selection: [
                                ["Lato", "Lato"],
                                ["Oswald", "Oswald"],
                            ],
                            default: "Lato",
                            string: "Fonts",
                        },
                    },
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("FontSelectionField");

    QUnit.test("FontSelectionField displays the correct fonts on options", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: '<form><field name="fonts" widget="font" placeholder="Placeholder"/></form>',
        });
        const options = target.querySelectorAll('.o_field_widget[name="fonts"] option');

        assert.strictEqual(
            target.querySelector('.o_field_widget[name="fonts"] > *').style.fontFamily,
            "Lato",
            "Widget font should be default (Lato)"
        );
        assert.strictEqual(options[0].value, "false", "Unselected option has no value");
        assert.strictEqual(
            options[0].textContent,
            "Placeholder",
            "Unselected option is the placeholder"
        );

        assert.strictEqual(
            options[1].style.fontFamily,
            "Lato",
            "Option 1 should have the correct font (Lato)"
        );
        assert.strictEqual(
            options[2].style.fontFamily,
            "Oswald",
            "Option 2 should have the correct font (Oswald)"
        );

        await editSelect(target, ".o_input", options[2].value);

        assert.strictEqual(
            target.querySelector('.o_field_widget[name="fonts"] > *').style.fontFamily,
            "Oswald",
            "Widget font should be updated (Oswald)"
        );
    });

    QUnit.test(
        "FontSelectionField displays one blank option (not required)",
        async function (assert) {
            serverData.models.partner.fields.fonts.selection = [
                [false, ""],
                ...serverData.models.partner.fields.fonts.selection,
            ];
            await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch: '<form><field name="fonts" widget="font"/></form>',
            });
            assert.containsN(target.querySelector(".o_field_widget[name='fonts']"), "option", 3);
        }
    );
});
