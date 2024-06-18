/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { ContentEditionDialog } from "@sale_pdf_quote_builder/js/content_edition/content_edition";

class CustomContentKanbanLike extends Component {
    static template = "sale_pdf_quote_builder.CustomContentKanbanLike";
    static props = {...standardFieldProps};
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
    }

    get datas() {
        return JSON.parse(this.props.record.data.customizable_pdf_form_fields);
    }

    async onClickEditText(documentType, formField) {
        console.log(documentType)
        console.log(formField)
        this.dialog.add(ContentEditionDialog, {
        });
    }

}

registry.category("fields").add("custom_content_kanban_like", {
    component: CustomContentKanbanLike,
    supportedTypes: ["char"],
});
// maybe char instead of json
