import { beforeEach, expect, test } from "@odoo/hoot";
import { animationFrame, mockTouch, runAllTimers } from "@odoo/hoot-mock";
import { EventBus } from "@odoo/owl";
import {
    defineModels,
    fields,
    mockService,
    models,
    mountView,
    swipeLeft,
    swipeRight,
} from "@web/../tests/web_test_helpers";
import { SIZES } from "@web/core/ui/ui_service";

class Project extends models.Model {
    foo = fields.Boolean({ string: "Foo" });
    bar = fields.Boolean({ string: "Bar" });
}
defineModels([Project]);

beforeEach(() => mockTouch(true));

test.tags("mobile")("swipe settings in mobile [REQUIRE TOUCHEVENT]", async () => {
    mockService("ui", (env) => {
        Object.defineProperty(env, "isSmall", {
            value: true,
        });
        return {
            bus: new EventBus(),
            get size() {
                return SIZES.XS;
            },
            get isSmall() {
                return true;
            },
        };
    });
    await mountView({
        type: "form",
        resModel: "project",
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

    await swipeLeft(".settings");
    await runAllTimers();
    await animationFrame();
    expect(".selected").toHaveAttribute("data-key", "project", {
        message: "current setting should be project",
    });

    await swipeRight(".settings");
    await runAllTimers();
    await animationFrame();
    expect(".selected").toHaveAttribute("data-key", "crm", {
        message: "current setting should be crm",
    });
});

test("swipe settings on larger screen sizes has no effect", async () => {
    mockService("ui", (env) => {
        Object.defineProperty(env, "isSmall", {
            value: false,
        });
        return {
            bus: new EventBus(),
            get size() {
                return SIZES.XXL;
            },
            get isSmall() {
                return false;
            },
        };
    });
    await mountView({
        type: "form",
        resModel: "project",
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

    await swipeLeft(".settings");
    await runAllTimers();
    await animationFrame();
    expect(".selected").toHaveAttribute("data-key", "crm", {
        message: "current setting should be crm",
    });
});
