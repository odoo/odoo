/** @odoo-module **/

import VariantMixin from "@website_sale/js/sale_variant_mixin";
import publicWidget from "@web/legacy/js/public/public_widget";
import { renderToFragment } from "@web/core/utils/render";

import "@website_sale/js/website_sale";

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
    let product_id = 0;
    // needed for list view of variants
    if (parent.querySelector('input.product_id:checked')) {
        product_id = parent.querySelector('input.product_id:checked').value;
    } else {
        product_id = parent.querySelector('.product_id').value;
    }
    const isMainProduct = combination.product_id &&
        (parent.classList.contains('.js_main_product') || parent.classList.contains('.main_product')) &&
        combination.product_id === parseInt(product_id);

    if (!this.isWebsite || !isMainProduct) {
        return;
    }

    const addQtyInput = parent.querySelector('input[name="add_qty"]');
    let qty = addQtyInput.value;
    let ctaWrapper = parent.querySelector('#o_wsale_cta_wrapper');
    ctaWrapper.classList.replace('d-none', 'd-flex');
    ctaWrapper.classList.remove('out_of_stock');

    if (combination.product_type === 'product' && !combination.allow_out_of_stock_order) {
        combination.free_qty -= parseInt(combination.cart_qty);
        addQtyInput.dataset.max = combination.free_qty || 1;;
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

    this.el.querySelectorAll('.oe_website_sale .availability_message_' + combination.product_template).forEach((elem) => {
        elem.remove();
    });
    combination.has_out_of_stock_message = combination.out_of_stock_message.textContent !== '';
    combination.out_of_stock_message = markup(combination.out_of_stock_message);
    this.el.querySelector('div.availability_messages').append(renderToFragment(
        'website_sale_stock.product_availability',
        combination
    ));
};

publicWidget.registry.WebsiteSale.include({
    /**
     * Adds the stock checking to the regular _onChangeCombination method
     * @override
     */
    _onChangeCombination: function () {
        this._super.apply(this, arguments);
        VariantMixin._onChangeCombinationStock.apply(this, arguments);
    },
    /**
     * Recomputes the combination after adding a product to the cart
     * @override
     */
    _onClickAdd(ev) {
        return this._super.apply(this, arguments).then(() => {
            if (this.el.querySelector('div.availability_messages').length) {
                this._getCombinationInfo(ev);
            }
        });
    }
});

export default VariantMixin;
