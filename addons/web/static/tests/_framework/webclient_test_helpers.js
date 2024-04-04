import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";

class TestClientAction extends Component {
    static template = xml`
        <div class="test_client_action">
            ClientAction_<t t-esc="props.action.params?.description"/>
        </div>`;
    static props = ["*"];
}

export function useTestClientAction() {
    const tag = "__test__client__action__";
    registry.category("actions").add(tag, TestClientAction);
    return {
        tag,
        target: "main",
        type: "ir.actions.client",
        params: { description: "Id 1" },
    };
}
