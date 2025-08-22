import VariantMixin from '@website_sale/js/variant_mixin';
import { renderToFragment } from '@web/core/utils/render';
import { formatFloat } from '@web/core/utils/numbers';
import { setElementContent } from '@web/core/utils/html';


import { markup } from "@odoo/owl";

/**
 * Addition to the variant_mixin._onChangeCombination
 *
 * This will prevent the user from selecting a quantity that is not available in the
 * stock for that product.
 *
 * It will also display various info/warning messages regarding the select product's stock.
 *
 * This behavior is only applied for the web shop (and not on the SO form)
 * and only for the main product.
 *
 * @param {MouseEvent} ev
 * @param {Element} parent
 * @param {Array} combination
 */
VariantMixin._onChangeCombinationStock = function (ev, parent, combination) {
    const has_max_combo_quantity = 'max_combo_quantity' in combination
    if (!combination.is_storable && !has_max_combo_quantity) {
        return;
    }

    if (!parent.matches('.js_main_product') || !combination.product_id) {
        // if we're not on product page or the product is dynamic
        return;
    }

    const addQtyInput = parent.querySelector('input[name="add_qty"]');
    let qty = addQtyInput.value;
    const ctaWrapper = parent.querySelector('#o_wsale_cta_wrapper');
    ctaWrapper.classList.replace('d-none', 'd-flex');
    ctaWrapper.classList.remove('out_of_stock');

    if (!combination.allow_out_of_stock_order) {
        combination.free_qty -= parseInt(combination.cart_qty);
        addQtyInput.dataset.max = combination.free_qty || 1;
        if (combination.free_qty < 0) {
            combination.free_qty = 0;
        }
        if (qty > combination.free_qty) {
            qty = combination.free_qty || 1;
            addQtyInput.value = qty;
        }
        if (combination.free_qty < 1) {
            ctaWrapper.classList.replace('d-flex', 'd-none');
            ctaWrapper.classList.add('out_of_stock');
        }
    }

    if (has_max_combo_quantity) {
        addQtyInput.dataset.max = combination.max_combo_quantity || 1;
        if (qty > combination.max_combo_quantity) {
            qty = combination.max_combo_quantity || 1;
            addQtyInput.value = qty;
        }
        if (combination.max_combo_quantity < 1) {
            ctaWrapper.classList.replace('d-flex', 'd-none');
            ctaWrapper.classList.add('out_of_stock');
        }
    }

    // needed xml-side for formatting of remaining qty
    combination.formatQuantity = (qty) => {
        if (Number.isInteger(qty)) {
            return qty;
        } else {
            const decimals = Math.max(
                0,
                Math.ceil(-Math.log10(combination.uom_rounding))
            );
            return formatFloat(qty, {digits: [false, decimals]});
        }
    }

    document.querySelector('.oe_website_sale')
        .querySelectorAll('.availability_message_' + combination.product_template)
        .forEach(el => el.remove());
    if (combination.out_of_stock_message) {
        combination.out_of_stock_message = markup(combination.out_of_stock_message);
        const outOfStockMessage = document.createElement('div');
        setElementContent(outOfStockMessage, combination.out_of_stock_message);
        combination.has_out_of_stock_message = !!outOfStockMessage.textContent.trim();
    }
    this.el.querySelector('div.availability_messages').append(renderToFragment(
        'website_sale_stock.product_availability', combination
    ));
};

export default VariantMixin;
