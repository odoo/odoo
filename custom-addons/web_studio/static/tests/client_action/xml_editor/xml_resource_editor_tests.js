/** @odoo-module **/

import { Component, reactive, xml } from "@odoo/owl";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { getFixture, mount, nextTick } from "@web/../tests/helpers/utils";
import { XmlResourceEditor } from "@web_studio/client_action/xml_resource_editor/xml_resource_editor";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { uiService } from "@web/core/ui/ui_service";
import { registry } from "@web/core/registry";

QUnit.module("XmlResourceEditor", (hooks) => {
    let target;

    hooks.beforeEach(() => {
        registry.category("services").add("ui", uiService).add("hotkey", hotkeyService);
        target = getFixture();
    });

    QUnit.test("can display warnings", async (assert) => {
        const mockRPC = (route, args) => {
            if (route === "/web_studio/get_xml_editor_resources") {
                return {
                    views: [
                        {
                            id: 1,
                            arch: "<data />",
                        },
                    ],
                };
            }
        };

        class Parent extends Component {
            static components = { XmlResourceEditor };
            static template = xml`<XmlResourceEditor displayAlerts="props.state.displayAlerts" onClose="() => {}" mainResourceId="1" />`;
        }

        const env = await makeTestEnv({ mockRPC });
        const state = reactive({ displayAlerts: true });
        await mount(Parent, target, { env, props: { state } });
        assert.containsOnce(target, ".o_web_studio_code_editor_info .alert.alert-warning");
        state.displayAlerts = false;
        await nextTick();
        assert.containsNone(target, ".o_web_studio_code_editor_info .alert.alert-warning");
    });
});
