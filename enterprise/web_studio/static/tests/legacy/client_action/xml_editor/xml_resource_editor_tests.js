/** @odoo-module **/

import { Component, reactive, useState, xml } from "@odoo/owl";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { getFixture, nextTick, click } from "@web/../tests/helpers/utils";
import { mountInFixture } from "@web/../tests/helpers/mount_in_fixture";
import { XmlResourceEditor } from "@web_studio/client_action/xml_resource_editor/xml_resource_editor";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { uiService } from "@web/core/ui/ui_service";
import { popoverService } from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";

QUnit.module("XmlResourceEditor", (hooks) => {
    let target;

    hooks.beforeEach(() => {
        registry
            .category("services")
            .add("ui", uiService)
            .add("hotkey", hotkeyService)
            .add("popover", popoverService);
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
            static props = ["*"];
        }

        const env = await makeTestEnv({ mockRPC });
        const state = reactive({ displayAlerts: true });
        await mountInFixture(Parent, target, { env, props: { state } });
        assert.containsOnce(target, ".o_web_studio_code_editor_info .alert.alert-warning");
        state.displayAlerts = false;
        await nextTick();
        assert.containsNone(target, ".o_web_studio_code_editor_info .alert.alert-warning");
    });

    QUnit.test("stores and restores the cursor position when reloading resources after save", async (assert) => {
        let arch = "<data>1\n2\n3\n4\n5\n</data>";
        const mockRPC = (route, args) => {
            if (route === "/web_studio/get_xml_editor_resources") {
                assert.step('load sources');
                return {
                    views: [
                        {
                            id: 1,
                            arch,
                        },
                    ],
                };
            }
        };

        class Parent extends Component {
            static components = { XmlResourceEditor };
            static template = xml`<XmlResourceEditor onClose="() => {}" mainResourceId="1" reloadSources="state.key" onSave.bind="onSave" onCodeChange="() => {}"/>`;
            static props = ["*"];

            setup() {
                this.state = useState({ key: 0 });
            }
            async onSave({newCode}) {
                await Promise.resolve();
                this.state.key++;
                arch = newCode;
            }
        }

        const env = await makeTestEnv({ mockRPC });
        await mountInFixture(Parent, target, { env });
        assert.verifySteps(["load sources"])

        const aceEl = target.querySelector(".o_web_studio_code_editor.ace_editor")
        const editor = window.ace.edit(aceEl);
        assert.deepEqual(editor.getCursorPosition(), {
            column: 0,
            row: 0,
        });
        editor.selection.moveToPosition({
            row: 3, column: 1
        });
        editor.insert("appended");

        await click(target.querySelector(".o_web_studio_xml_resource_selector .btn-primary"));
        await nextTick();
        assert.verifySteps(["load sources"])

        const newAceEl = target.querySelector(".o_web_studio_code_editor.ace_editor");
        const newEditor = window.ace.edit(newAceEl);
        assert.notEqual(aceEl, newAceEl);
        assert.notEqual(editor, newEditor);

        assert.deepEqual(newEditor.getCursorPosition(), {
            column: 1,
            row: 3
        });
    });
});
