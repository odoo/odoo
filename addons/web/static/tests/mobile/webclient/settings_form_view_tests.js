/** @odoo-module **/

import { getFixture, mockTimeout, nextTick } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { swipeLeft, swipeRight } from "@web/../tests/mobile/helpers";
import { registry } from "@web/core/registry";

import { EventBus } from "@odoo/owl";

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
                    <app string="CRM" name="crm">
                        <block>
                            <setting help="this is bar">
                                <field name="bar"/>
                            </setting>
                        </block>
                    </app>
                    <app string="Project" name="project">
                        <block>
                            <setting help="this is foo">
                                <field name="foo"/>
                            </setting>
                        </block>
                    </app>
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
                    <app string="CRM" name="crm">
                        <block>
                            <setting help="this is bar">
                                <field name="bar"/>
                            </setting>
                        </block>
                    </app>
                    <app string="Project" name="project">
                        <block>
                            <setting help="this is foo">
                                <field name="foo"/>
                            </setting>
                        </block>
                    </app>
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
