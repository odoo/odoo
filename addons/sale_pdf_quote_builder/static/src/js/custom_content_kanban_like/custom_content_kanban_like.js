import { reactive, useEffect } from '@odoo/owl';
import { _t } from '@web/core/l10n/translation';
import { registry } from '@web/core/registry';
import { JsonField, jsonField } from '@web/views/fields/jsonb/jsonb';

class CustomContentKanbanLike extends JsonField {
    static template = 'sale_pdf_quote_builder.CustomContentKanbanLike';

    setup() {
        this.state = reactive(
            JSON.parse(this.props.record.data[this.props.name]),
            () => this.onChange(JSON.stringify(this.state))
        );
        this.placeholderLabel = _t("Click to write content for the PDF quote...");

        useEffect(value => {
            const { header, line, footer } = JSON.parse(value);
            this.state.header = header;
            this.state.line = line;
            this.state.footer = footer;
        }, () => [this.props.record.data[this.props.name]]);
    }

    onChange(newValue) {
        this.props.record.update({ [this.props.name]: newValue });
    }
}

export const CustomContentKanbanLikeField = {
    ...jsonField,
    component: CustomContentKanbanLike,
};

registry.category('fields').add('custom_content_kanban_like', CustomContentKanbanLikeField);
