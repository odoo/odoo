/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PartnerAutoCompleteMany2one, partnerAutoCompleteMany2one } from "@partner_autocomplete/js/partner_autocomplete_many2one";
import { markup } from "@odoo/owl";

export class PurchaseOrderVendorConformation extends PartnerAutoCompleteMany2one {
    setup() {
        super.setup();
    }

    async updateRecord(value) {
        super.updateRecord(value);
        const records = this.props.record.data.order_line.records;
        if (records.length === 0 || records[0].data.product_id == false) {
            return;
        }
        await this.props.record.save()
        if (!this.props.record.data.partner_id) {
            return;
        }
        await this.showConfirmationDialog(value);
    }

    async showConfirmationDialog(value) {
        return await new Promise(async resolve => {
            const message = _t("The selected vendor has diffrent price. Do you want to apply it ?")
            const purchse_data = this.props.record.data;
            const orderLineRecords = await this.orm.call(this.props.record.resModel, 'js_vendor_conformation_record', [purchse_data.id, value[0]], {});
            const updatedOrderLines = purchse_data.order_line.records.filter(orderLine =>
                orderLineRecords.find(record => record.product_name == orderLine.data.name)
            );

            const tableRows = orderLineRecords.map(record => `
                <tr>
                    <td>${record.product_name}</td>
                    <td>${record.current_price}</td>
                    <td>${record.new_price}</td>
                </tr>
            `).join('');

            if (orderLineRecords.length != 0){
                this.dialog.add(ConfirmationDialog, {
                    title: _t("Update price"),
                    body: markup(
                        `<div>${message}</div>
                        <table class="table" border="1">
                            <thead style="background-color:#efeded;font-size:medium;font-weight: 800;color:black;">
                                <th class="col-md-6">Product</th>
                                <th class="col-md-3">Current Price</th>
                                <th class="col-md-3">New Price</th>
                            </thead>
                            <tbody>
                                ${tableRows}
                            </tbody>
                        </table>`
                    ),
                    confirmLabel: _t("Update"),
                    confirm: async () => {
                        await Promise.all(updatedOrderLines.map(record => (
                            record.update({'price_unit': 0, 'date_planned': false, 'old_price_unit': 0}),
                            record.update({'product_qty': record.data.product_qty})
                            ),
                        ));
                        await this.props.record.save();
                    },
                    cancelLabel: _t("Keep as is"),
                    cancel: async () => {
                        await Promise.all(updatedOrderLines.map(record => (
                            record.update({'old_price_unit': 0})
                            ),
                        ));
                        resolve(false)
                    },
                });
            }
        });
    }
}

export const purchaseVendorMany2OneField = {
    ...partnerAutoCompleteMany2one,
    component: PurchaseOrderVendorConformation,
};

registry.category("fields").add("purchase_vendor_many2one", purchaseVendorMany2OneField);
