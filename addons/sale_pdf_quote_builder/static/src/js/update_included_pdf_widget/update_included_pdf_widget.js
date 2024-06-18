import { Component } from '@odoo/owl';
import {
    UpdateIncludedPdfDialog
} from '@sale_pdf_quote_builder/js/update_included_pdf_dialog/update_included_pdf_dialog';
import { registry } from '@web/core/registry';
import { x2ManyCommands } from '@web/core/orm_service';
import { useService } from '@web/core/utils/hooks';
import { standardWidgetProps } from '@web/views/widgets/standard_widget_props';

export class UpdateIncludedPdfWidget extends Component {
    static template = 'salePdfQuoteBuilder.UpdateIncludedPdfWidget';
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        this.dialog = useService('dialog');
        this.orm = useService('orm');
    }

    async onClick() {
        await this.props.record.save();
        const dialogParams = await this.orm.call(
            'sale.order', 'get_update_included_pdf_params', [this.props.record.resId]
        )
        const savePdfs = async (selectedPdfs) => {
            for (const line of selectedPdfs.lines) {
                const sol = this.props.record.data.order_line.records.find(
                    sol => sol.resId === line.id
                );
                sol._noUpdateParent = true;  // Ensure that no rpc will be made to save the changes
                await sol.update(
                    // save is needed to ensure that no onChange call will be made
                    {product_document_ids: [x2ManyCommands.set(line.selectedPdfs)]}, { save: true }
                );
            }
            this.props.record.data.order_line._onUpdate({withoutOnchange: true});

            await this.props.record.update({
                quotation_document_ids: [
                    x2ManyCommands.set(selectedPdfs.header.concat(selectedPdfs.footer))
                ],
            }, { save: true }); // This one will save :)
        };
        this.dialog.add(UpdateIncludedPdfDialog, {...dialogParams, savePdfs});
    }
}

export const updateIncludedPdfWidget = {
    component: UpdateIncludedPdfWidget,
};

registry.category('view_widgets').add('updateIncludedPdfWidget', updateIncludedPdfWidget);
