/** @odoo-module */

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { formatFacebookReactions } from "@social_facebook/js/utils";

export class SocialFacebookReactions extends Component {
    static template = "SocialFacebookReactions";
    static props = standardFieldProps;

    get mostUsedReactions() {
        return formatFacebookReactions(JSON.parse(this.props.record.data[this.props.name] || []), 2)
            .map((reaction) => reaction[0])
            .join("");
    }
}

registry.category("fields").add("social_facebook_reactions", {
    component: SocialFacebookReactions,
});
