/** @odoo-module **/
import { click, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
import { EventBus } from "@odoo/owl";

const serviceRegistry = registry.category("services");

let serverData;
let target;

QUnit.module("Worksheet", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        hex_color: { string: "hexadecimal color", type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                        },
                        {
                            id: 2,
                            hex_color: "#ff4444",
                        },
                    ],
                },
            },
        };
        setupViewRegistries();
    });

    QUnit.module("OpenStudioButton");

    QUnit.test("button opens studio", async function (assert) {
        assert.expect(7);
        const bus = new EventBus();
        const modelFormAction = {
            name: "fakeFormAction",
            view_mode: "tree,form"
        }

        const fakeStudioService = {
            start() {
                return {
                    open(...args) {
                        bus.trigger("studio:open", args);
                    },
                };
            },
        };
        const fakeActionService = {
            start() {
                return {
                    async doAction(action) {
                        assert.deepEqual(action, modelFormAction, "action service must receive the doAction call");
                        return true;
                    },
                };
            },
        };
        const fakeUIService = {
            start(env) {
                const ui = {
                    bus: new EventBus(),
                    block() {
                        assert.step("block ui");
                    },
                    unblock() {
                        assert.step("unblock ui");
                    },
                };
                Object.defineProperty(env, "isSmall", {
                    get() {
                        return true;
                    },
                });
                return ui;
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });
        serviceRegistry.add("studio", fakeStudioService);
        serviceRegistry.add("ui", fakeUIService);

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
                <form>
                    <header>
                        <widget name="open_studio_button"/>
                    </header>
                    <group>
                        <field name="hex_color" widget="color" />
                    </group>
                </form>`,
            mockRPC(route) {
                if (route === "/web/dataset/call_kw/worksheet.template/get_x_model_form_action") {
                    assert.step("get_x_model_form_action");
                    return modelFormAction;
                }
            },
        });

        bus.addEventListener("studio:open", () => {
            assert.step("open studio");
        });

        assert.containsOnce(
            target,
            ".o_widget_open_studio_button button",
            "widget button is present in the view"
        );

        await click(target.querySelector(".o_widget_open_studio_button button"));
        assert.verifySteps([
            "block ui",
            "get_x_model_form_action",
            "open studio",
            "unblock ui"
        ]);
    });

});
