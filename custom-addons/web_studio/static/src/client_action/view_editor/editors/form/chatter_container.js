/** @odoo-module */

import { Chatter } from "@mail/core/web/chatter";

import { Component } from "@odoo/owl";

export class ChatterContainer extends Chatter {
    onClick(ev) {
        this.env.config.onNodeClicked(this.props.studioXpath);
    }
}
ChatterContainer.template = "web_studio.ChatterContainer";
ChatterContainer.props = [...Chatter.props, "studioXpath?"];

export class ChatterContainerHook extends Component {
    onClick() {
        this.env.viewEditorModel.doOperation({
            type: "chatter",
            model: this.env.viewEditorModel.resModel,
            ...this.props.chatterData,
        });
    }
}
ChatterContainerHook.template = "web_studio.ChatterContainerHook";
ChatterContainerHook.components = { Chatter };
ChatterContainerHook.props = {
    chatterData: Object,
    threadModel: String,
};
