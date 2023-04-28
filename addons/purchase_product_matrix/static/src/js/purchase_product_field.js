/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PurchaseOrderLineProductField } from '@purchase_product_configurator/js/purchase_product_field';
import { ProductMatrixDialog } from "@product_matrix/js/product_matrix_dialog";
import { useService } from "@web/core/utils/hooks";


patch(PurchaseOrderLineProductField.prototype, {

    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
    },

    async _openGridConfigurator(edit) {
        const PurchaseOrderRecord = this.props.record.model.root;
        // fetch matrix information from server;
        await PurchaseOrderRecord.update({
            grid_product_tmpl_id: this.props.record.data.product_template_id,
        });

        let updatedLineAttributes = [];
        if (edit) {
            // provide attributes of edited line to automatically focus on matching cell in the matrix
            for (let ptnvav of this.props.record.data.product_no_variant_attribute_value_ids.records) {
                updatedLineAttributes.push(ptnvav.resId);
            }
            for (let ptav of this.props.record.data.product_template_attribute_value_ids.records) {
                updatedLineAttributes.push(ptav.resId);
            }
            updatedLineAttributes.sort((a, b) => { return a - b; });
        }

        this._openMatrixConfigurator(
            PurchaseOrderRecord.data.grid,
            this.props.record.data.product_template_id[0],
            updatedLineAttributes,
        );

        if (!edit) {
            // remove new line used to open the matrix
            PurchaseOrderRecord.data.order_line.delete(this.props.record);
        }
    },

    async _openProductConfigurator(edit=false) {
        if (edit && this.props.record.data.purchase_add_mode == 'matrix_purchase') {
            this._openGridConfigurator(true);
        } else {
            super._openProductConfigurator(...arguments)
        }
    },

    _openMatrixConfigurator(jsonInfo, productTemplateId, editedCellAttributes) {
        const infos = JSON.parse(jsonInfo);
        this.dialog.add(ProductMatrixDialog, {
            header: infos.header,
            rows: infos.matrix,
            editedCellAttributes: editedCellAttributes.toString(),
            product_template_id: productTemplateId,
            record: this.props.record.model.root,
        });
    }
});
