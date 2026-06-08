import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ReturnOrderDialog } from "@sale_stock/return_order_dialog/return_order_dialog";

patch(ReturnOrderDialog.prototype, {

    /**
     * @override  of `sale_stock` to add a download shipping label button when a shipping label is
     * available.
     *
     * @param {Object[]} selectedLines - The selected product lines to return.
     * @returns {Object}
     */
    _getReturnLabelDialogProps(selectedLines) {
        const dialogProps = super._getReturnLabelDialogProps(selectedLines);
        const shippingLabelUrl = this._getShippingLabelUrl(selectedLines);
        if (!shippingLabelUrl) {
            return dialogProps;
        }
        return {
            ...dialogProps,
            cancelLabel: _t("Download Shipping Label"),
            cancel: () => window.open(selectedLines[0].shipping_label_url, "_blank"),
        };
    },

    /**
     * @override of `sale_stock` to add `hasShippingLabel` if a shipping label is available.
     *
     * @param {Object[]} selectedLines
     * @returns {Object}
     */
    _getReturnLabelInfoProps(selectedLines) {
        return {
            ...super._getReturnLabelInfoProps(selectedLines),
            hasShippingLabel: !!this._getShippingLabelUrl(selectedLines),
        };
    },

    /**
     * Return the shipping label URL if all selected lines belong to the same picking and that
     * picking has a label, otherwise return null.
     *
     * @param {Object[]} selectedLines
     * @returns {string|null}
     */
    _getShippingLabelUrl(selectedLines) {
        const shippingLabelUrl = selectedLines[0]?.shipping_label_url;
        const allLinesFromSamePicking = selectedLines.every(
            line => line.picking_id === selectedLines[0].picking_id
        );
        return allLinesFromSamePicking ? shippingLabelUrl : null;
    },

});
