/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { SocialPostFormatterMixin } from "../social_post_formatter_mixin";
import { Component, markup } from "@odoo/owl";

export class PostFormatterField extends SocialPostFormatterMixin(Component) {
    get formattedPost() {
        return markup(this._formatPost(this.props.record.data[this.props.name] || ''));
    }
}
PostFormatterField.template = 'social.PostFormatterField';
PostFormatterField.props = {
    ...standardFieldProps,
};

export const postFormatterField = {
    component: PostFormatterField,
};

registry.category("fields").add("social_post_formatter", postFormatterField);
