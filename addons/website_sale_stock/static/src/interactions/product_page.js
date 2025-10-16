import { rpc } from '@web/core/network/rpc';
import { isEmail } from '@web/core/utils/strings';
import { patch } from '@web/core/utils/patch';
import { renderToFragment } from '@web/core/utils/render';
import { formatFloat } from '@web/core/utils/numbers';
import { setElementContent } from '@web/core/utils/html';
import { patchDynamicContent } from '@web/public/utils';
import { markup } from '@odoo/owl';
import { ProductPage } from '@website_sale/interactions/product_page';

patch(ProductPage.prototype, {
    setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            '#product_stock_notification_message': {
                't-on-click': this.onClickProductStockNotificationMessage.bind(this),
            },
            '#product_stock_notification_form_submit_button': {
                't-on-click': this.onClickSubmitProductStockNotificationForm.bind(this),
            },
            'button[name="add_to_cart"]': {
                't-on-product_added_to_cart': this._getCombinationInfo.bind(this),
            },
        });
    },

    onClickProductStockNotificationMessage(ev) {
        const partnerEmail = document.querySelector('#wsale_user_email').value;
        const emailInputEl = document.querySelector('#stock_notification_input');

        emailInputEl.value = partnerEmail;
        this._handleClickStockNotificationMessage(ev);
    },

    onClickSubmitProductStockNotificationForm(ev) {
        const productId = parseInt(ev.currentTarget.dataset.productId);
        this._handleClickSubmitStockNotificationForm(ev, productId);
    },

    _handleClickStockNotificationMessage(ev) {
        ev.currentTarget.classList.add('d-none');
        ev.currentTarget.parentElement.querySelector('#stock_notification_form').classList.remove('d-none');
    },

    async _handleClickSubmitStockNotificationForm(ev, productId) {
        const stockNotificationEl = ev.currentTarget.closest('#stock_notification_div');
        const formEl = stockNotificationEl.querySelector('#stock_notification_form');
        const email = stockNotificationEl.querySelector('#stock_notification_input').value.trim();

        if (!isEmail(email)) {
            return this._displayEmailIncorrectMessage(stockNotificationEl);
        }

        try {
            await this.waitFor(rpc(
                '/shop/add/stock_notification', { product_id: productId, email }
            ));
        } catch {
            this._displayEmailIncorrectMessage(stockNotificationEl);
            return;
        }
        const message = stockNotificationEl.querySelector('#stock_notification_success_message');
        message.classList.remove('d-none');
        formEl.classList.add('d-none');
    },

    _displayEmailIncorrectMessage(stockNotificationEl) {
        const incorrectIconEl = stockNotificationEl.querySelector('#stock_notification_input_incorrect');
        incorrectIconEl.classList.remove('d-none');
    },

    /**
     * Override of `website_sale` to check the product's stock.
     *
     * This will prevent the user from selecting a quantity that is not in stock for that product.
     *
     * It will also display various info/warning messages regarding the select product's stock.
     *
     * @param {Event} ev
     * @param {Element} parent
     * @param {Object} combination
     */
    async _onChangeCombination(ev, parent, combination) {
        await super._onChangeCombination(...arguments);
        const has_max_combo_quantity = 'max_combo_quantity' in combination
        if (!combination.is_storable && !has_max_combo_quantity) return;
        if (!combination.product_id) return; // If the product is dynamic.

        const addQtyInput = parent.querySelector('input[name="add_qty"]');
        const qty = parseFloat(addQtyInput?.value) || 1;
        const ctaWrapper = parent.querySelector('#o_wsale_cta_wrapper');
        ctaWrapper.classList.replace('d-none', 'd-flex');
        ctaWrapper.classList.remove('out_of_stock');

        if (!combination.allow_out_of_stock_order) {
            const unavailableQty = await this.waitFor(this._getUnavailableQty(combination));
            combination.free_qty -= unavailableQty;
            if (combination.free_qty < 0) {
                combination.free_qty = 0;
            }
            if (addQtyInput) {
                addQtyInput.dataset.max = combination.free_qty || 1;
                if (qty > combination.free_qty) {
                    addQtyInput.value = addQtyInput.dataset.max;
                }
            }
            if (combination.free_qty < 1) {
                ctaWrapper.classList.replace('d-flex', 'd-none');
                ctaWrapper.classList.add('out_of_stock');
            }
        } else if (has_max_combo_quantity) {
            if (addQtyInput) {
                addQtyInput.dataset.max = combination.max_combo_quantity || 1;
                if (qty > combination.max_combo_quantity) {
                    addQtyInput.value = addQtyInput.dataset.max;
                }
            }
            if (combination.max_combo_quantity < 1) {
                ctaWrapper.classList.replace('d-flex', 'd-none');
                ctaWrapper.classList.add('out_of_stock');
            }
        }

        // needed xml-side for formatting of remaining qty
        combination.formatQuantity = qty => {
            if (Number.isInteger(qty)) {
                return qty;
            } else {
                const decimals = Math.max(0, Math.ceil(-Math.log10(combination.uom_rounding)));
                return formatFloat(qty, { digits: [false, decimals] });
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
    },

    async _getUnavailableQty(combination) {
        return parseInt(combination.cart_qty);
    },
});
