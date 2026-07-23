import { Component, t, useProps, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { ActionContainer } from "@web/webclient/actions/action_container";

export class ActionScreen extends Component {
    static components = { ActionContainer };
    props = useProps({
        actionName: t.string(),
        viewMode: t.string().optional(),
    });
    static storeOnOrder = false;
    static template = xml`
        <div class="o_web_client">
            <ActionContainer/>
        </div>
    `;
}

registry.category("pos_pages").add("ActionScreen", {
    name: "ActionScreen",
    component: ActionScreen,
    route: `/pos/ui/${odoo.pos_config_id}/action/{string:actionName}`,
    params: {},
});
