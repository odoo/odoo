/** @odoo-module */

import { Chatter } from "@mail/chatter/web_portal/chatter";

import { Component } from "@odoo/owl";

export class ChatterContainer extends Chatter {
    static template = "web_studio.ChatterContainer";
    static props = [...Chatter.props, "studioXpath?"];

    onClick(ev) {
        this.env.config.onNodeClicked(this.props.studioXpath);
    }
}

export class ChatterContainerHook extends Component {
    static template = "web_studio.ChatterContainerHook";
    static components = { Chatter };
    static props = {
        chatterData: Object,
        threadModel: String,
    };

    onClick() {
        this.env.viewEditorModel.doOperation({
            type: "chatter",
            model: this.env.viewEditorModel.resModel,
            ...this.props.chatterData,
        });
    }
}
