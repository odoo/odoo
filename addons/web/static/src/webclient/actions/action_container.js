/** @odoo-module **/

import { Component, xml, useEffect, useSubEnv } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";
import { ControlPanel } from "@web/search/control_panel/control_panel";

// -----------------------------------------------------------------------------
// ActionContainer (Component)
// -----------------------------------------------------------------------------
export class ActionContainer extends Component {
    static components = { ControlPanel };
    static template = xml`
    <t t-name="web.ActionContainer">
      <div class="o_action_manager">
        <t t-if="state.value.Component" t-component="state.value.Component" className="'o_action'" t-props="state.value.componentProps" t-key="state.value.id"/>
        <t t-else="">
            <t t-if="state.value.displayEmptyPanel and !env.isSmall">
                <ControlPanel display="{disableDropdown: true}">
                    <t t-set-slot="layout-buttons">
                        <button class="btn btn-primary invisible"> empty </button>
                    </t>
                </ControlPanel>
            </t>
        </t>
      </div>
    </t>`;
    static props = {};

    setup() {
        const self = this;
        let isRendered = false;
        let next = null;
        let value = {};
        this.state = {
            get value() {
                return value;
            },
            set value(newValue) {
                if (!isRendered && !value.Component && newValue.Component) {
                    next = newValue;
                } else {
                    value = newValue;
                    next = null;
                    isRendered = false;
                    self.render();
                }
            },
        };
        useEffect(() => {
            isRendered = true;
            if (next) {
                this.state.value = next;
            }
        });
        useSubEnv({ config: { breadcrumbs: [], noBreadcrumbs: true } });
        useBus(this.env.bus, "ACTION_MANAGER:UPDATE", ({ detail: info }) => {
            this.state.value = info;
        });
    }
}
