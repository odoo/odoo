/** @odoo-module **/

import { JsonField, jsonField } from "@web/views/fields/jsonb/jsonb";
import { _t } from "@web/core/l10n/translation";
import { onWillStart, useState } from "@odoo/owl";
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";

import { ContentEditionDialog } from "@sale_pdf_quote_builder/js/content_edition/content_edition";

class CustomContentKanbanLike extends JsonField {
    static template = "sale_pdf_quote_builder.CustomContentKanbanLike";

    setup() {
        this.state = useState({
            datas: {},
        });
        this.dialog = useService("dialog");
        this.placeholderLabel = _t("Click to write content for the PDF quote...");

        onWillStart(async () => {
            this.state.datas = await this._loadData();
        });
    }

    async _loadData() {
        return JSON.parse(this.props.record.data.customizable_pdf_form_fields);
    }

    async onClickEditText(documentType, formField, content) {
        this.dialog.add(ContentEditionDialog, {
            saleOrderId: this.props.record.evalContext.id,
            documentType: documentType,
            formField: formField,
            content: content,
            placeholderLabel : this.placeholderLabel,
        });
    }

}

export const CustomContentKanbanLikeField = {
    ...jsonField,
    component: CustomContentKanbanLike,
};

registry.category("fields").add("custom_content_kanban_like", CustomContentKanbanLikeField);
