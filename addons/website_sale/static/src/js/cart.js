import { Component } from "@odoo/owl";
import { ProductCombo } from '@sale/js/models/product_combo';
import { serializeComboItem } from '@sale/js/sale_utils';
import { browser } from "@web/core/browser/browser";
import { serializeDateTime } from '@web/core/l10n/dates';
import { rpc } from "@web/core/network/rpc";
import { debounce } from "@web/core/utils/timing";
import { redirect } from "@web/core/utils/urls";
import publicWidget from "@web/legacy/js/public/public_widget";

import wSaleUtils from "@website_sale/js/website_sale_utils";


publicWidget.registry.websiteSaleCart = publicWidget.Widget.extend({
    selector: '#shop_cart',
    events: {
        'change input.js_quantity[data-product-id]': '_onChangeCartQuantity',
        'click .js_delete_product': '_onClickDeleteProduct',
        'click button.js_add_suggested_products': '_onClickSuggestedProduct',
        'click button.js_add_quick_reorder_products': '_onClickQuickReorderProduct',
        'input input.quick-reorder-qty': '_onQuickQtyInput',
        'keydown .quick-reorder-qty': '_onQuickQtyKeydown',
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        this._changeCartQuantity = debounce(this._changeCartQuantity.bind(this), 500);

        if (sessionStorage.getItem('keepQuickReorderOpen') === 'true') {
            sessionStorage.removeItem('keepQuickReorderOpen');
            document.querySelector('#quick_reorder_dropdown')?.classList.remove('collapsed');
            document.querySelector('#quick_reorder_products')?.classList.add('show');
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onChangeCartQuantity: function (ev) {
        var $input = $(ev.currentTarget);
        if ($input.data('update_change')) {
            return;
        }
        var value = parseInt($input.val() || 0, 10);
        if (isNaN(value)) {
            value = 1;
        }
        var $dom = $input.closest('tr');
        var $dom_optional = $dom.nextUntil(':not(.optional_product.info)');
        var line_id = parseInt($input.data('line-id'), 10);
        var productIDs = [parseInt($input.data('product-id'), 10)];
        this._changeCartQuantity($input, value, $dom_optional, line_id, productIDs);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickDeleteProduct: function (ev) {
        ev.preventDefault();
        $(ev.currentTarget).closest('.o_cart_product').find('.js_quantity').val(0).trigger('change');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickSuggestedProduct: function (ev) {
        const dataset = ev.currentTarget.dataset;

        this.call('cart', 'add', {
            productTemplateId: parseInt(dataset.productTemplateId, 10),
            productId: parseInt(dataset.productId, 10),
            isCombo: dataset.productType === 'combo',
        }, {
            isBuyNow: true,
            showQuantity: Boolean(dataset.showQuantity),
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickQuickReorderProduct: async function (ev) {
        const dataset = ev.currentTarget.dataset;

        const productTemplateId = parseInt(dataset.productTemplateId, 10);
        const productId = parseInt(dataset.productId, 10);
        const qty = parseInt(dataset.quantity);
        const isCombo = dataset.productType === 'combo';
        const selectedComboItems = JSON.parse(dataset.selectedComboItems || '[]');

        const currentIndex = [
          ...document.querySelectorAll(".quick-reorder-qty"),
        ].indexOf(ev.currentTarget.previousElementSibling);

        let linkedProducts;
        let quantity = qty

        if (isCombo) {
            const { combos, quantity: updatedQty } = await rpc(
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

        const payload = {
            product_template_id: productTemplateId,
            product_id: productId,
            quantity: quantity,
            ...(isCombo && { linked_products: linkedProducts }),
        };

        const data = await rpc('/shop/cart/quick/add', payload);

        if(!document.querySelector('.o_total_card')){
            sessionStorage.setItem('keepQuickReorderOpen', 'true');
            redirect('/shop/cart');
        }
        wSaleUtils.updateCartNavBar(data);

        // Move focus to the next quantity input and select its contents
        const nextInput = [...document.querySelectorAll('.quick-reorder-qty')][currentIndex];
        if (nextInput) {
            nextInput.focus();
            nextInput.select();
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onQuickQtyInput: function(ev) {
        const input = ev.currentTarget;
        const lineId = input.dataset.lineId;
        const orderId = input.dataset.orderId;
        const priceUnit = parseFloat(input.dataset.priceUnit);
        const digits = parseInt(input.dataset.currencyDigits, 10);

        let qty = parseInt(input.value);
        if (isNaN(qty)) qty = 0;

        const addButton = document.querySelector(`#quick_reorder_${orderId}_${lineId}`);
        if (addButton) {
            if (qty <= 0) {
                addButton.classList.add('disabled');
            } else {
                addButton.classList.remove('disabled');
                addButton.dataset.quantity = qty;
                const total = (qty * priceUnit).toFixed(digits);
                document.querySelector(
                    `#total_price_${orderId}_${lineId} .oe_currency_value`
                ).textContent = total;
            }
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onQuickQtyKeydown: function(ev) {
        if (ev.key === 'Enter') {
            const lineId = ev.currentTarget.dataset.lineId;
            const orderId = ev.currentTarget.dataset.orderId;

            const addButton = document.querySelector(`#quick_reorder_${orderId}_${lineId}`);
            if (addButton && !addButton.classList.contains('disabled')) {
                addButton.click();
            }
        }
    },
    /**
     * @private
     */
    _changeCartQuantity: function ($input, value, $dom_optional, line_id, productIDs) {
        $($dom_optional).toArray().forEach((elem) => {
            $(elem).find('.js_quantity').text(value);
            productIDs.push($(elem).find('span[data-product-id]').data('product-id'));
        });
        $input.data('update_change', true);

        rpc('/shop/cart/update', {
            line_id: line_id,
            product_id: parseInt($input.data('product-id'), 10),
            quantity: value,
        }).then((data) => {
            $input.data('update_change', false);
            var check_value = parseInt($input.val() || 0, 10);
            if (isNaN(check_value)) {
                check_value = 1;
            }
            if (value !== check_value) {
                $input.trigger('change');
                return;
            }
            if (!data.cart_quantity) {
                // Ensures last cart removal is recorded
                browser.sessionStorage.setItem('website_sale_cart_quantity', 0);
                return window.location = '/shop/cart';
            }
            $input.val(data.quantity);
            $('.js_quantity[data-line-id='+line_id+']').val(data.quantity).text(data.quantity);

            wSaleUtils.updateCartNavBar(data);
            wSaleUtils.showWarning(data.warning);
            // Propagating the change to the express checkout forms
            Component.env.bus.trigger('cart_amount_changed', [data.amount, data.minor_amount]);
        });
    },
});

export default publicWidget.registry.websiteSaleCart;
