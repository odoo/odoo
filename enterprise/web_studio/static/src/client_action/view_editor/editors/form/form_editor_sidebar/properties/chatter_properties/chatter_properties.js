/** @odoo-module */

import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { Property } from "@web_studio/client_action/view_editor/property/property";
import { SidebarPropertiesToolbox } from "@web_studio/client_action/view_editor/interactive_editor/properties/sidebar_properties_toolbox/sidebar_properties_toolbox";

export class ChatterProperties extends Component {
    static template = "web_studio.ViewEditor.InteractiveEditorProperties.Chatter";
    static components = { Property, SidebarPropertiesToolbox };
    static props = ["node"];

    setup() {
        this.state = useState({});

        onWillStart(async () => {
            const alias = await this.getMailAlias(this.props.node);
            this.state.mailAlias = alias.email_alias;
            this.state.aliasDomain = alias.alias_domain;
        });

        onWillUpdateProps(async (nextProps) => {
            const alias = await this.getMailAlias(nextProps.node);
            this.state.mailAlias = alias.email_alias;
            this.state.aliasDomain = alias.alias_domain;
        });
    }

    async getMailAlias(node) {
        const mailAliasObj = await rpc("/web_studio/get_email_alias", {
            model_name: this.env.viewEditorModel.resModel,
        });
        return mailAliasObj;
    }

    onChangeMailAlias(value) {
        rpc("/web_studio/set_email_alias", {
            model_name: this.env.viewEditorModel.resModel,
            value,
        });
    }
}
