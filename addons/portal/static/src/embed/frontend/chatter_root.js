/* @odoo-module */

import { Chatter } from "@mail/chatter/web_portal/chatter";

import { Component, xml, useSubEnv } from "@odoo/owl";

export class ChatterRoot extends Component {
    static template = xml`
        <Chatter threadId="props.resId" threadModel="props.resModel" hasComposer="props.hasComposer" twoColumns="props.twoColumns"/>
    `;
    static components = { Chatter };
    static props = ["resId, resModel", "dataToken", "hasComposer", "twoColumns", "displayRating"];

    setup() {
        useSubEnv({
            inShadow: true,
            ShadowRootId: "chatterRoot",
            displayRating: this.props.displayRating,
        });
    }
}
