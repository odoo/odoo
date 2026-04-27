/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

export class SocialPostSplitPerMedia extends Component {
    static template = "social.SocialPostSplitPerMedia";
    static props = standardFieldProps;

    onClick() {
        this.props.record.update({ [this.props.name]: true });
    }
}

export const socialPostSplitPerMedia = {
    component: SocialPostSplitPerMedia,
    supportedTypes: ["boolean"],
};

registry.category("fields").add("social_post_split_per_media", socialPostSplitPerMedia);
