import { render } from "@web/owl2/utils";
import { Component, xml, useListener } from "@odoo/owl";

// -----------------------------------------------------------------------------
// ActionContainer (Component)
// -----------------------------------------------------------------------------
export const actionContainerProps = {};

export class ActionContainer extends Component {
    static template = xml`
        <t t-name="web.ActionContainer">
          <div class="o_action_manager">
            <t t-if="this.info.Component" t-component="this.info.Component" className="'o_action'" t-props="this.info.componentProps" t-key="this.info.id"/>
          </div>
        </t>`;

    setup() {
        this.info = {};
        this.onActionManagerUpdate = ({ detail: info }) => {
            this.info = info;
            render(this);
        };
        useListener(this.env.bus, "ACTION_MANAGER:UPDATE", this.onActionManagerUpdate);
    }
}
