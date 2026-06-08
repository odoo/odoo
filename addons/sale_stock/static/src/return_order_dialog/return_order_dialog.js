import { Component, onWillStart, proxy } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { formatCurrency } from "@web/core/currency";
import { renderToMarkup } from "@web/core/utils/render";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { QuantityButtons } from "@sale/js/quantity_buttons/quantity_buttons";

export class ReturnOrderDialog extends Component {
    static components = { Dialog, WarningDialog, QuantityButtons };
    static template = "sale_stock.ReturnOrderDialog";
    static props = {
        saleOrderId: Number,
        accessToken: String,
        close: Function,
    };

    setup() {
        this.dialog = useService("dialog");
        this.state = proxy({ returnableLines: [], returnReasonId: null });

        onWillStart(async () => {
            this.orderReturnData = await this._loadData();
            this.state.returnableLines = this.orderReturnData.returnable_lines;
            this.formatCurrency = (amount) => formatCurrency(
                amount, this.orderReturnData.currency_id
            );
        });
    }

    //--------------------------------------------------------------------------
    // Data Exchanges
    //--------------------------------------------------------------------------

    /**
     * Fetch the return data for the current order.
     *
     * @returns {Promise<Object>}
     */
    async _loadData() {
        const data = await rpc("/my/order/return_data", {
            order_id: this.props.saleOrderId,
            access_token: this.props.accessToken,
        });
        if (data.error) {
            window.location.href = "/my";
        }
        return data;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Clamp the quantity of a return line between 0 and its remaining deliverable quantity.
     *
     * @param {Object} line - The return line to update.
     * @param {number} quantity - The requested quantity.
     */
    setQuantity(line, quantity) {
        line.quantity = Math.min(Math.max(quantity, 0), line.remaining_delivered_qty);
    }

    /**
     * Update the selected reason id.
     *
     * @param {Event} ev
     */
    updateReturnReason(ev) {
        this.state.returnReasonId = ev.target.value;
    }

    /**
     * Open the confirmation dialog for downloading the return label.
     */
    openReturnLabelDialog() {
        const selectedLines = this.state.returnableLines.filter(line => line.quantity);
        this.dialog.add(ConfirmationDialog, this._getReturnLabelDialogProps(selectedLines));
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @param {Object[]} selectedLines - Selected product lines for return.
     * @returns {Object} Props for the return label dialog.
     */
    _getReturnLabelDialogProps(selectedLines) {
        return {
            title: _t("Print the return request label."),
            body: renderToMarkup(
                "sale_stock.ReturnLabelInfo", this._getReturnLabelInfoProps(selectedLines)
            ),
            confirmLabel: _t("Download Return Label"),
            confirm: () => this._downloadReturnLabel(selectedLines),
            size: "md",
        };
    }

    /**
     * @returns {Object} Template props for the ReturnLabelInfo template.
     */
    _getReturnLabelInfoProps() {
        return {
            companyName: this.orderReturnData.company_name,
            warehouseAddress: this.orderReturnData.warehouse_address,
        };
    }

    /**
     * Open the return label in a new tab.
     *
     * @param {Object[]} selectedLines - Selected product lines for return.
     */
    _downloadReturnLabel(selectedLines) {
        const returnDetails = Object.fromEntries(
            selectedLines.map(line => [line.move_id, line.quantity])
        );
        const params = {
            access_token: this.props.accessToken,
            return_details: JSON.stringify(returnDetails),
            return_reason_id: this.state.returnReasonId,
        }
        const query = new URLSearchParams(params).toString();
        window.open(`${ this.orderReturnData.download_label_url }?${ query }`, "_blank");
    }


    //--------------------------------------------------------------------------
    // Getters
    //--------------------------------------------------------------------------

    /**
     * @returns {boolean} True if at least one line has a quantity and a return reason is selected.
     */
    get isReadyToContinue() {
        return (
            this.state.returnableLines.some(line => line.quantity > 0) && this.state.returnReasonId
        );
    }
}
