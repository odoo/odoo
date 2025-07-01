import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { WebClient } from "@web/webclient/webclient";
import { mountWithCleanup } from "./component_test_helpers";

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

/**
 * @param {Parameters<typeof mountWithCleanup>[1]} [options]
 */
export async function mountWebClient(options) {
    await mountWithCleanup(WebClient, options);
    // Wait for visual changes caused by a potential loadState
    await animationFrame();
    // wait for BlankComponent
    await animationFrame();
    // wait for the regular rendering
    await animationFrame();
}
