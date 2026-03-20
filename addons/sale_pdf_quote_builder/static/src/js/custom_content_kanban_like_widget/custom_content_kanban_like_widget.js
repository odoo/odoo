import { Component, useEffect, useState } from "@odoo/owl";
import {
    CustomFieldCard
} from "@sale_pdf_quote_builder/js/custom_content_kanban_like_widget/custom_field_card/custom_field_card";
import { x2ManyCommands } from "@web/core/orm_service";
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class CustomContentKanbanLikeWidget extends Component {
    static components = { CustomFieldCard };
    static template = "sale_pdf_quote_builder.CustomContentKanbanLike";
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            headers: {},
            lines: {},
            footers: {},
        });

        // Initialize the state and update available documents when updating the quotation template.
        useEffect((saleOrderTemplate) => {
            this.updateState();
        }, () => [this.props.record.data.sale_order_template_id]);

        // Make quotation tab readonly on confirmation
        useEffect((saleOrderState) => {
            if (saleOrderState === 'sale') {
                this.props.readonly = true;
                this.props.record.save(); // trigger refresh to update form
            }
        }, () => [this.props.record.data.state]);

    }

    async updateState() {
        const saved = await this.props.record.save();  // To display documents of potentially unsaved SOL.
        if (saved) {  // do not fetch wrong form data if record was not saved.
            const { headers, lines, footers } = await this.orm.call(
                'sale.order', 'get_update_included_pdf_params', [this.props.record.resId]
            )
            this.state.headers = headers;
            this.state.lines = lines;
            this.state.footers = footers;
        }
    }

    updateJson() {
        const selectedHeaders = this.state.headers.files.filter(f => f.is_selected);
        const selectedFooters = this.state.footers.files.filter(f => f.is_selected);
        const value = JSON.stringify({
            'header': Object.assign({}, ...selectedHeaders.map(header => {
                return {
                    [header.id]: {
                        document_name: header.name,
                        custom_form_fields: Object.assign({}, ...header.custom_form_fields.map(
                            formField => ({[formField.name]: formField.value})
                        )),
                    }
            }})),
            'line': Object.assign({}, ...this.state.lines.map(line => {
                return {
                    [line.id]: Object.assign({}, ...line.files.filter(f => f.is_selected).map(doc => {
                        return {
                            [doc.id]: {
                                document_name: doc.name,
                                custom_form_fields: Object.assign({}, ...doc.custom_form_fields.map(
                                    formField => ({[formField.name]: formField.value})
                                )),
                            }
                    }})),
            }})),
            'footer': Object.assign({}, ...selectedFooters.map(footer => {
                return {
                    [footer.id]: {
                        document_name: footer.name,
                        custom_form_fields: Object.assign({}, ...footer.custom_form_fields.map(
                            formField => ({[formField.name]: formField.value})
                        )),
                    }
            }})),
        })
        this.props.record.update({ ['customizable_pdf_form_fields']: value });
    }

    async saveProductDocument(lineId, docId, isSelected) {
        if (this.props.readonly) {
            return;
        }
        const sol = this.props.record.data.order_line.records.find(
            sol => sol.resId === lineId
        );
        sol._noUpdateParent = true; // Ensure that no rpc will be made to save the changes
        if (isSelected) {
            // save is needed to ensure that no onChange call will be made
            await sol.update({product_document_ids: [x2ManyCommands.link(docId)]}, { save: true });
        } else {
            // save is needed to ensure that no onChange call will be made
            await sol.update({product_document_ids: [x2ManyCommands.unlink(docId)]}, { save: true });
        }
        await this.props.record.data.order_line._onUpdate({withoutOnchange: true});
        this.updateJson();
    };

    async saveQuotationDocument(docId, isSelected) {
        if (this.props.readonly) {
            return;
        }
        if (isSelected) {
            await this.props.record.update({
                quotation_document_ids: [
                    x2ManyCommands.link(docId),
                ],
            });
        } else {
            await this.props.record.update({
                quotation_document_ids: [
                    x2ManyCommands.unlink(docId),
                ],
            });
        }
        this.updateJson();
    };
}

export const customContentKanbanLikeWidget = {
    component: CustomContentKanbanLikeWidget,
};

registry.category("view_widgets").add(
    "customContentKanbanLikeWidget", customContentKanbanLikeWidget
);
