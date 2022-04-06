/** @odoo-module */

import OptionalProductsModal from 'sale_product_configurator.OptionalProductsModal'
import { _t } from 'web.core'
import { sprintf } from "@web/core/utils/strings";

OptionalProductsModal.include({

    _computeFooterEnabled: function () {
        const footer = document.querySelector('.modal-content footer');
        const selectedProducts = document.querySelectorAll('.js_product.in_cart');
        for(let product of selectedProducts){
            if(product.querySelector('.modal-content .input-group.d-none')){
                footer.classList.add('d-none');
                return;
            }
        }
        footer.classList.remove('d-none');
    },

    _onAddOrRemoveOption(ev){
        this._super(...arguments);
        this._computeFooterEnabled();
    },

    _onChangeCombination: function (ev, $parent, combination) {
        const result = this._super(...arguments);

        if (!this.isWebsite || !$parent.is('.in_cart') || !(combination.product_type === "product")) return;

        // Get all html elements to modify.
        const addQtyInput = $parent.find('.js_quantity')[0];
        const addQtyContainer = addQtyInput.parentNode;

        // Get existing message or create it.
        let warningMessage = addQtyContainer.parentNode.querySelector('p');

        if (!warningMessage) {
            warningMessage = document.createElement('p');
            warningMessage.classList.add('text-warning', 'd-none', 'pt-2');

            addQtyContainer.parentNode.appendChild(warningMessage);
        }

        const quantity = parseInt(addQtyInput.value);
        const resultingValue = combination.free_qty - (quantity + combination.cart_qty);

        addQtyInput.parentNode.classList.remove('d-none');

        if(combination.show_availability && combination.free_qty <= combination.available_threshold){
            warningMessage.classList.remove('d-none');
            warningMessage.innerText = sprintf(_t('%s %s left.'), combination.free_qty, combination.uom_name);
        }

        if(resultingValue <= 0){
            warningMessage.classList.remove('d-none');
            addQtyInput.value = Math.max(combination.free_qty, 1);
        }

        if(combination.free_qty - combination.cart_qty <= 0){
            warningMessage.innerText = _t('Out of stock');
            addQtyInput.parentNode.classList.add('d-none');
        }

        this._computeFooterEnabled();
        return result;
    }
});
