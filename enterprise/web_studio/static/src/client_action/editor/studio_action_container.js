/** @odoo-module **/

import { ActionContainer } from "@web/webclient/actions/action_container";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { KeepLast } from "@web/core/utils/concurrency";
import { Component, markup, onWillStart, onWillUnmount, onWillUpdateProps, xml } from "@odoo/owl";
import { useStudioServiceAsReactive } from "@web_studio/studio_service";
import { resetViewCompilerCache } from "@web/views/view_compiler";

const editorTabRegistry = registry.category("web_studio.editor_tabs");

export class StudioActionContainer extends Component {
    static props = {
        ...ActionContainer.props,
        reloadId: { type: Number },
    };

    static template = xml`
        <t t-name="web.ActionContainer">
        <div class="o_action_manager">
            <t t-if="info.Component" t-component="info.Component" className="'o_action'" t-props="info.componentProps" t-key="info.id"/>
        </div>
        </t>`;

    setup() {
        this.actionService = useService("action");
        this.studio = useStudioServiceAsReactive();
        this.info = {};

        let actionKey = 1;
        const onUiUpdate = ({ detail: info }) => {
            this.info = info;
            actionKey++;
            this.render();
        };
        this.env.bus.addEventListener("ACTION_MANAGER:UPDATE", onUiUpdate);
        onWillUnmount(() => this.env.bus.removeEventListener("ACTION_MANAGER:UPDATE", onUiUpdate));

        const doAction = async (action, options) => {
            try {
                await this.actionService.doAction(action, options);
                this.actionKey = actionKey;
            } catch (e) {
                if (action !== "web_studio.action_editor") {
                    // Fallback on the actionEditor, except if the actionEditor crashes
                    this.studio.setParams({ editorTab: "views" });
                }
                // Rethrow anyway: the error doesn't originates from a user's action
                throw e;
            }
        };

        onWillStart(async () => {
            const action = await this.getStudioAction();
            this.studioKey = this.studio.requestId;
            doAction(action);
            await Promise.resolve();
        });

        const willUpdateKeepLast = new KeepLast();
        onWillUpdateProps(async () => {
            if (this.studio.requestId !== this.studioKey || this.actionKey !== actionKey) {
                const action = await willUpdateKeepLast.add(this.getStudioAction());
                resetViewCompilerCache();
                return new Promise((_resolve) => {
                    const resolve = () => {
                        this.env.bus.removeEventListener("ACTION_MANAGER:UPDATE", resolve);
                        _resolve();
                    };
                    this.studioKey = this.studio.requestId;
                    doAction(action, { clearBreadcrumbs: true, noEmptyTransition: true }).finally(
                        () => {
                            this.env.bus.removeEventListener("ACTION_MANAGER:UPDATE", resolve);
                        }
                    );
                    this.env.bus.addEventListener("ACTION_MANAGER:UPDATE", resolve);
                });
            }
        });
    }
    async getStudioAction() {
        const { editorTab, editedAction, editedReport, editedViewType } = this.studio;
        const tab = editorTabRegistry.get(editorTab);
        if (editorTab === "views") {
            if (editedViewType) {
                return "web_studio.view_editor";
            }
            return tab.action;
        }
        if (tab.action) {
            const action = tab.action;
            return action instanceof Function ? action(this.env) : action;
        } else if (editorTab === "reports" && editedReport) {
            return "web_studio.report_editor";
        } else {
            const action = await rpc("/web_studio/get_studio_action", {
                action_name: editorTab,
                model: editedAction.res_model,
                view_id: editedAction.view_id && editedAction.view_id[0], // Not sure it is correct or desirable
            });
            action.help = action.help && markup(action.help);
            return action;
        }
    }
}
