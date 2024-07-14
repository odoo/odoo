/** @odoo-module **/

import { SocialPostFormatterMixin } from "./social_post_formatter_mixin";

import { HtmlField, htmlField } from "@web_editor/js/backend/html_field";
import { registry } from "@web/core/registry";
import { markup } from "@odoo/owl";

export class FieldPostPreview extends SocialPostFormatterMixin(HtmlField) {
    get markupValue() {
        const $html = $(this.props.record.data[this.props.name] + '');
        $html.find('.o_social_preview_message').each((index, previewMessage) => {
            $(previewMessage).html(this._formatPost($(previewMessage).text().trim()));
        });

        return markup($html[0].outerHTML);
    }
}

FieldPostPreview.props = {
    ...FieldPostPreview.props,
    mediaType: { type: String, optional: true },
};

export const fieldPostPreview = {
    ...htmlField,
    component: FieldPostPreview,
    extractProps({ attrs }) {
        const props = htmlField.extractProps(...arguments);
        props.mediaType = attrs.media_type || '';
        return props;
    },
};

registry.category("fields").add("social_post_preview", fieldPostPreview);
