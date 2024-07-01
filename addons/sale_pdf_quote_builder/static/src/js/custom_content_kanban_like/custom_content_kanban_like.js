/** @odoo-module **/

import { JsonField, jsonField } from "@web/views/fields/jsonb/jsonb";
import { _t } from "@web/core/l10n/translation";
import { reactive } from "@odoo/owl";
import { registry } from '@web/core/registry';

class CustomContentKanbanLike extends JsonField {
    static template = "sale_pdf_quote_builder.CustomContentKanbanLike";

    setup() {
        this.state = reactive(
            JSON.parse(this.props.record.data[this.props.name]),
            () => this.onChange(JSON.stringify(this.state))
        );
        this.placeholderLabel = _t("Click to write content for the PDF quote...");
    }

    onChange(newValue) {
        this.props.record.update({ [this.props.name]: newValue });
    }
}

export const CustomContentKanbanLikeField = {
    ...jsonField,
    component: CustomContentKanbanLike,
};

registry.category("fields").add("custom_content_kanban_like", CustomContentKanbanLikeField);
