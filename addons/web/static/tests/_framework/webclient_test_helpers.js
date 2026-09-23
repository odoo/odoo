// @ts-check

import { animationFrame } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { ActionContainer } from "@web/webclient/actions/action_container";
import { WebClient } from "@web/webclient/webclient";

import { mountWithCleanup } from "./component_test_helpers.js";

class TestClientAction extends Component {
    static template = xml`
        <div class="test_client_action">
            ClientAction_<t t-out="this.props.action.params?.description"/>
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
 * @returns {Promise<ActionContainer>}
 */
export async function mountActionHost(options = {}) {
    return mountWithCleanup(ActionContainer, options);
}

/** @param {Parameters<typeof mountWithCleanup>[1] & { WebClient?: typeof WebClient }} [options] */
export async function mountWebClient(options = {}) {
    const { WebClient: WebClientComponent = WebClient, ...mountOptions } = options;
    const webClient = await mountWithCleanup(WebClientComponent, mountOptions);
    await animationFrame();
    await animationFrame();
    await animationFrame();

    return webClient;
}
