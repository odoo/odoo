import { ProductCombo } from '@sale/js/models/product_combo';
import { serializeComboItem } from '@sale/js/sale_utils';
import { serializeDateTime } from '@web/core/l10n/dates';
import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { Interaction } from '@web/public/interaction';
import wSaleUtils from '@website_sale/js/website_sale_utils';

export class QuickReorder extends Interaction {

    static selector = '#quick_reorder_sidebar';
    dynamicContent = {
        '.o_wsale_quick_reorder_qty_input': {
            't-on-input': this.updateQuantityAndPrice,
            't-on-keydown': this.triggerReorderOnEnter,
        },
        '.o_wsale_quick_reorder_product_button': { 't-on-click': this.reorderProduct },
    };

    /**
     * Update the total price and enable/disable the add button based on the quantity input.
     *
     * @param {Event} ev
     * @return {void}
     */
    async updateQuantityAndPrice(ev) {
        const qtyInput = ev.currentTarget;
        const priceUnit = parseFloat(qtyInput.dataset.priceUnit);
        const digits = parseInt(qtyInput.dataset.currencyDigits, 10);
        const qty = parseInt(qtyInput.value, 10) || 0;
        this._updateAddButton(qtyInput, qty);
        if (qty > 0) {
            this._updateTotalPrice(qtyInput, qty, priceUnit, digits);
        }
    }

    /**
     * Update the add button state based on quantity.
     *
     * @private
     * @param {Element} qtyInput - The quantity input element.
     * @param {number} qty - The quantity value.
     * @return {void}
     */
    _updateAddButton(qtyInput, qty) {
        const addButton = qtyInput.closest('.o_wsale_quick_reorder_line').querySelector(
            '.o_wsale_quick_reorder_product_button'
        );
        const isDisabled = qty <= 0;
        addButton.classList.toggle('disabled', isDisabled);
        if (qty > 0) {
            addButton.dataset.quantity = String(qty);
        }
    }

    /**
     * Update the total price display for the related line.
     *
     * @private
     * @param {Element} qtyInput - The quantity input element.
     * @param {number} qty - The quantity.
     * @param {number} priceUnit - The unit price.
     * @param {number} digits - The number of decimal digits for the currency.
     * @return {void}
     */
    _updateTotalPrice(qtyInput, qty, priceUnit, digits) {
        const priceEl = qtyInput.closest('.o_wsale_quick_reorder_line').querySelector(
            '.o_wsale_quick_reorder_product_price .oe_currency_value'
        );
        if (priceEl) {
            const totalPrice = (qty * priceUnit).toFixed(digits);
            priceEl.textContent = totalPrice;
        }
    }

    /**
     * Trigger the reorder action when Enter key is pressed on quantity input.
     *
     * @param {Event} ev
     * @return {void}
     */
    async triggerReorderOnEnter(ev) {
        if (ev.key !== 'Enter') return;

        const addButton = ev.currentTarget.closest('.o_wsale_quick_reorder_line').querySelector(
            '.o_wsale_quick_reorder_product_button'
        );
        if (addButton && !addButton.classList.contains('disabled')) {
            addButton.click();
        }
    }

    /**
     * Reorder the product and update the page's content.
     *
     * @param {Event} ev
     * @return {void}
     */
    async reorderProduct(ev) {
        // Extract product data from the button dataset.
        const addButtonDataset = ev.currentTarget.dataset;
        const productTemplateId = parseInt(addButtonDataset.productTemplateId, 10);
        const productId = parseInt(addButtonDataset.productId, 10);
        let quantity = parseInt(addButtonDataset.quantity);
        const isCombo = addButtonDataset.productType === 'combo';
        const selectedComboItems = JSON.parse(addButtonDataset.selectedComboItems || '[]');

        // Capture the button index before DOM updates.
        const allButtons = document.querySelectorAll('.o_wsale_quick_reorder_product_button');
        const currentButtonIndex = Array.from(allButtons).indexOf(ev.currentTarget);

        // Process combo products if applicable.
        let linkedProducts = [];
        if (isCombo) {
            const { quantity: updatedQty, combos } = await rpc(
                '/website_sale/combo_configurator/get_data',
                {
                    product_tmpl_id: productTemplateId,
                    quantity: quantity,
                    date: serializeDateTime(luxon.DateTime.now()),
                    selected_combo_items: selectedComboItems,
                }
            );
            quantity = updatedQty;
            linkedProducts = combos
                .map(combo => new ProductCombo(combo).selectedComboItem)
                .filter(Boolean)
                .map(comboItem => ({
                    product_template_id: comboItem.product.product_tmpl_id,
                    parent_product_template_id: productTemplateId,
                    quantity: quantity,
                    ...serializeComboItem(comboItem),
                }));
        }

        const data = await this.waitFor(rpc('/shop/cart/quick_add', {
            product_template_id: productTemplateId,
            product_id: productId,
            quantity: quantity,
            ...(isCombo && { linked_products: linkedProducts }),
        }));

        // Add the product to the cart and update the DOM.
        const cart = document.getElementById('shop_cart');
        // `updateCartNavBar` regenerates the cart lines and `updateQuickReorderSidebar`
        // regenerates the quick reorder products, so we need to stop and start interactions to
        // make sure the regenerated reorder products and cart lines are properly handled.
        this.services['public.interactions'].stopInteractions(cart);
        wSaleUtils.updateCartNavBar(data);
        wSaleUtils.updateQuickReorderSidebar(data);
        this.services['public.interactions'].startInteractions(cart);

        // Move the focus to the next quantity input.
        this._focusNextQuantityInput(currentButtonIndex);
    }

    /**
     * Moves the focus to the next quantity input.
     *
     * @param {HTMLElement} buttonIndex - The index of the reorder button that was clicked before
     *                                    DOM updates.
     * @return {void}
     */
    _focusNextQuantityInput(buttonIndex) {
        const allQuantityInputs = document.querySelectorAll('.o_wsale_quick_reorder_qty_input');
        const nextInput = allQuantityInputs[buttonIndex];
        if (nextInput) {
            nextInput.focus();
            nextInput.select();
        }
    }

}

registry
    .category('public.interactions')
    .add('website_sale.quick_reorder', QuickReorder);
