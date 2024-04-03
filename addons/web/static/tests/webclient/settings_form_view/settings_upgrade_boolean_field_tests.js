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
                    <field name="bar" widget="upgrade_boolean"/>
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
                    <div class="o_field">
                        <field name="bar" widget="upgrade_boolean"/>
                    </div>
                    <div class="o_label"><label for="bar"/><div>Coucou</div></div>
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
            ".o_label .badge",
            "the upgrade badge should be inside the label section"
        );
        assert.strictEqual(
            target.querySelector(".o_label").textContent,
            "BarEnterpriseCoucou",
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
                    <field name="bar" widget="upgrade_boolean"/>
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
                    <div class="o_field">
                        <field name="bar" widget="upgrade_boolean"/>
                    </div>
                    <div class="o_label"><label for="bar"/><div>Coucou</div></div>
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
                ".o_label .badge",
                "the upgrade badge shouldn't be inside the label section"
            );
            assert.strictEqual(
                target.querySelector(".o_label").textContent,
                "BarCoucou",
                "the label shouldn't contains the upgrade label"
            );
        }
    );
});
