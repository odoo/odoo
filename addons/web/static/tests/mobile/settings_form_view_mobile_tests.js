/** @odoo-module **/

import { getFixture, mockTimeout, nextTick } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { swipeLeft, swipeRight } from "@web/../tests/mobile/helpers";
import { registry } from "@web/core/registry";

const { EventBus } = owl;

let serverData, target;

const serviceRegistry = registry.category("services");

QUnit.module("Mobile SettingsFormView", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                project: {
                    fields: {
                        foo: { string: "Foo", type: "boolean" },
                        bar: { string: "Bar", type: "boolean" },
                    },
                },
            },
        };
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.module("BaseSettings Mobile");

    QUnit.test("swipe settings in mobile [REQUIRE TOUCHEVENT]", async function (assert) {
        const { execRegisteredTimeouts } = mockTimeout();
        serviceRegistry.add("ui", {
            start(env) {
                Object.defineProperty(env, "isSmall", {
                    value: true,
                });
                return {
                    bus: new EventBus(),
                    size: 0,
                    isSmall: true,
                };
            },
        });
        await makeView({
            type: "form",
            resModel: "project",
            serverData,
            arch: `
                <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                    <div class="o_setting_container">
                        <div class="settings">
                            <div class="app_settings_block" string="CRM" data-key="crm">
                                <div class="row mt16 o_settings_container">
                                    <div class="col-12 col-lg-6 o_setting_box">
                                        <div class="o_setting_left_pane">
                                            <field name="bar"/>
                                        </div>
                                        <div class="o_setting_right_pane">
                                            <label for="bar"/>
                                            <div class="text-muted">this is bar</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="app_settings_block" string="Project" data-key="project">
                                <div class="row mt16 o_settings_container">
                                    <div class="col-12 col-lg-6 o_setting_box">
                                        <div class="o_setting_left_pane">
                                            <field name="foo"/>
                                        </div>
                                        <div class="o_setting_right_pane">
                                            <label for="foo"/>
                                            <div class="text-muted">this is foo</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </form>`,
        });

        await swipeLeft(target, ".settings");
        execRegisteredTimeouts();
        await nextTick();
        assert.hasAttrValue(
            target.querySelector(".selected"),
            "data-key",
            "project",
            "current setting should be project"
        );

        await swipeRight(target, ".settings");
        execRegisteredTimeouts();
        await nextTick();
        assert.hasAttrValue(
            target.querySelector(".selected"),
            "data-key",
            "crm",
            "current setting should be crm"
        );
    });

    QUnit.test(
        "swipe settings on larger screen sizes has no effect [REQUIRE TOUCHEVENT]",
        async function (assert) {
            const { execRegisteredTimeouts } = mockTimeout();
            serviceRegistry.add("ui", {
                start(env) {
                    Object.defineProperty(env, "isSmall", {
                        value: false,
                    });
                    return {
                        bus: new EventBus(),
                        size: 9,
                        isSmall: false,
                    };
                },
            });
            await makeView({
                type: "form",
                resModel: "project",
                serverData,
                arch: `
                <form string="Settings" class="oe_form_configuration o_base_settings" js_class="base_settings">
                    <div class="o_setting_container">
                        <div class="settings">
                            <div class="app_settings_block" string="CRM" data-key="crm">
                                <div class="row mt16 o_settings_container">
                                    <div class="col-12 col-lg-6 o_setting_box">
                                        <div class="o_setting_left_pane">
                                            <field name="bar"/>
                                        </div>
                                        <div class="o_setting_right_pane">
                                            <label for="bar"/>
                                            <div class="text-muted">this is bar</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="app_settings_block" string="Project" data-key="project">
                                <div class="row mt16 o_settings_container">
                                    <div class="col-12 col-lg-6 o_setting_box">
                                        <div class="o_setting_left_pane">
                                            <field name="foo"/>
                                        </div>
                                        <div class="o_setting_right_pane">
                                            <label for="foo"/>
                                            <div class="text-muted">this is foo</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </form>`,
            });

            await swipeLeft(target, ".settings");
            execRegisteredTimeouts();
            await nextTick();
            assert.hasAttrValue(
                target.querySelector(".selected"),
                "data-key",
                "crm",
                "current setting should still be crm"
            );
        }
    );
});
