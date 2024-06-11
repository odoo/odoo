/** @odoo-module **/
import { click, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("SettingsUpgradeBoolean", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                "res.config.settings": {
                    fields: {
                        bar: { string: "Bar", type: "boolean" },
                    },
                },
            },
        };
        target = getFixture();
        setupViewRegistries();
    });
    QUnit.test("widget upgrade_boolean in a form view - dialog", async function (assert) {
        await makeView({
            type: "form",
            arch: `
                <form js_class="base_settings">
                    <app string="CRM" name="crm">
                        <field name="bar" widget="upgrade_boolean"/>
                    </app>
                </form>`,
            serverData,
            resModel: "res.config.settings",
        });

        await click(target.querySelector(".o-checkbox .form-check-input"));

        assert.containsOnce(
            target,
            ".o_dialog .modal",
            "the 'Upgrade to Enterprise' dialog should be opened"
        );
    });

    QUnit.test("widget upgrade_boolean in a form view - label", async function (assert) {
        await makeView({
            type: "form",
            arch: `
                <form js_class="base_settings">
                    <app string="CRM" name="crm">
                        <setting string="Coucou">
                            <field name="bar" widget="upgrade_boolean"/>
                        </setting>
                    </app>
                </form>`,
            serverData,
            resModel: "res.config.settings",
        });

        assert.containsNone(
            target,
            ".o_field .badge",
            "the upgrade badge shouldn't be inside the field section"
        );
        assert.containsOnce(
            target,
            ".o_form_label .badge",
            "the upgrade badge should be inside the label section"
        );
        assert.strictEqual(
            target.querySelector(".o_form_label").textContent,
            "CoucouEnterprise",
            "the upgrade label should be inside the label section"
        );
    });

    QUnit.test(
        "widget upgrade_boolean in a form view - dialog (enterprise version)",
        async function (assert) {
            patchWithCleanup(odoo, { info: { isEnterprise: 1 } });
            await makeView({
                type: "form",
                arch: `
                <form js_class="base_settings">
                    <app string="CRM" name="crm">
                        <field name="bar" widget="upgrade_boolean"/>
                    </app>
                </form>`,
                serverData,
                resModel: "res.config.settings",
            });

            await click(target.querySelector(".o-checkbox .form-check-input"));

            assert.containsNone(
                target,
                ".o_dialog .modal",
                "the 'Upgrade to Enterprise' dialog shouldn't be opened"
            );
        }
    );

    QUnit.test(
        "widget upgrade_boolean in a form view - label (enterprise version)",
        async function (assert) {
            patchWithCleanup(odoo, { info: { isEnterprise: 1 } });
            await makeView({
                type: "form",
                arch: `
                <form js_class="base_settings">
                    <app string="CRM" name="crm">
                        <setting string="Coucou">
                            <field name="bar" widget="upgrade_boolean"/>
                        </setting>
                    </app>
                </form>`,
                serverData,
                resModel: "res.config.settings",
            });

            assert.containsNone(
                target,
                ".o_field .badge",
                "the upgrade badge shouldn't be inside the field section"
            );
            assert.containsNone(
                target,
                ".o_form_label .badge",
                "the upgrade badge shouldn't be inside the label section"
            );
            assert.strictEqual(
                target.querySelector(".o_form_label").textContent,
                "Coucou",
                "the label shouldn't contains the upgrade label"
            );
        }
    );
});
