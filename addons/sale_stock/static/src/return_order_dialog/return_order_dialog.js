import { Component, onWillStart, useState, markup } from '@odoo/owl';
import { Dialog } from '@web/core/dialog/dialog';
import { WarningDialog } from '@web/core/errors/error_dialogs';
import { useService } from '@web/core/utils/hooks';
import {
    AlertDialog, ConfirmationDialog
} from '@web/core/confirmation_dialog/confirmation_dialog';
import { formatCurrency } from '@web/core/currency';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { QuantityButtons } from '@sale/js/quantity_buttons/quantity_buttons';
import { download } from '@web/core/network/download';

export class ReturnOrderDialog extends Component {
    static components = { Dialog, WarningDialog, QuantityButtons };
    static template = 'sale_stock.ReturnOrderDialog';
    static props = {
        saleOrderId: Number,
        accessToken: String,
        close: Function,
    };

    setup() {
        this.dialog = useService('dialog');
        this.orm = useService('orm');
        this.state =  useState({ products: [] });
        this.title = _t("Request a return");

        onWillStart(async () => {
            this.content = await this._loadData();
            this.state.products = this.content.products;
            this.formatCurrency = formatCurrency;
        });
    }

    //--------------------------------------------------------------------------
    // Data Exchanges
    //--------------------------------------------------------------------------

    async _loadData() {
        return rpc('/return/order/content', {
            order_id: this.props.saleOrderId,
            access_token: this.props.accessToken,
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    setQuantity(product, quantity) {
        if (quantity < 0) {
            quantity = 0;
        } else if (quantity > product.order_qty) {
            quantity = product.order_qty;
        }
        if (product.quantity === quantity) {
            return false;
        }
        product.quantity = quantity;
        return true;
    }

    onReturnReasonChange() {
        const returnReason = document.querySelector('select[name="return_reason"]');
        returnReason.classList.remove('is-invalid');
    }

    async onContinue() {
        const returnReason = document.querySelector('select[name="return_reason"]');
        const returnReasonValue = returnReason.value;
        if (!returnReasonValue) {
            returnReason.classList.add('is-invalid');
            returnReason.focus();
            return;
        }
        const errorMessage = this._getErrorMessage();
        if (errorMessage) {
            this.dialog.add(AlertDialog, {
                title: _t("Invalid Operation"),
                body: errorMessage
            });
            return;
        }
        const selectedProducts = this.state.products.filter(product => product.quantity);
        this.dialog.add(ConfirmationDialog, {
            title: '',
            body: markup(
                _t("<strong>Print the return request label.</strong><br/>") +
                _t("Add this label in your package and send it to this address:<br/><br/>") +
                `<strong>${this.content.company_name}</strong><br/>${this.content.warehouse_address}`
            ),
            confirmLabel: _t("Download Label"),
            confirm: async () => {
                const params = {
                    order_id: this.props.saleOrderId,
                    access_token: this.props.accessToken,
                    selected_products: JSON.stringify(selectedProducts),
                    return_reason: returnReasonValue,
                }
                if (selectedProducts.length <= 10) {
                    const query = new URLSearchParams(params).toString();
                    const url = `return_order/download_label?${query}`;
                    window.open(url, '_blank');
                } else {
                    await download({url: 'return_order/download_label', data: params});
                }
                this.props.close();
            },
        });
    }

    _getErrorMessage() {
        const noSelectedProduct = this.state.products.every(
            product => Number(product.quantity || 0) === 0
        );
        if (noSelectedProduct) {
            return _t("Please add at least one product to return.");
        }

        return false;
    }

}
