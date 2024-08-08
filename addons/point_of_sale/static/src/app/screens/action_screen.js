import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { ActionContainer } from "@web/webclient/actions/action_container";

export class ActionScreen extends Component {
    static components = { ActionContainer };
    static props = {};
    static storeOnOrder = false;
    static template = xml`
        <ActionContainer/>
    `;
}
registry.category("pos_screens").add("ActionScreen", ActionScreen);
