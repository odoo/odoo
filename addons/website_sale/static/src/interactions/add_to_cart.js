import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import wSaleUtils from '@website_sale/js/website_sale_utils';

export class AddToCart extends Interaction {
    static selector = '#add_to_cart, #buy_now, .o_wsale_products_page button[name="add_to_cart"]';
    dynamicContent = {
        _root: { "t-on-click.prevent": this.locked(this.addToCart, true) },
    };

    /**
     * Add a product to the cart.
     *
     * @param {MouseEvent} ev
     */
    async addToCart(ev) {
        const el = ev.currentTarget;
        const form = wSaleUtils.getClosestProductForm(el);

        const quantity = await this.waitFor(this.services['cart'].add({
            productTemplateId: parseInt(el.dataset.productTemplateId),
            productId: parseInt(el.dataset.productId),
            isCombo: el.dataset.productType === 'combo',
            quantity: parseFloat(form.querySelector('input[name="add_qty"]')?.value) || 1,
            uomId: parseInt(form.querySelector('input[name="uom_id"]:checked')?.value),
            ptavs: this._getSelectedPtavs(form),
            productCustomAttributeValues: this._getCustomPtavValues(form),
            noVariantAttributeValues: this._getSelectedNoVariantPtavs(form),
            ...this._getOptionalParams(form),
        }, {
            isBuyNow: el.id === 'buy_now',
            isConfigured: el.parentElement.id === 'add_to_cart_wrap',
            showQuantity: el.dataset.showQuantity === 'True',
        }));

        if (quantity > 0) {
            el.dispatchEvent(new CustomEvent('product_added_to_cart', { bubbles: true }));
        }

        return quantity;
    }

    /**
     * Hook to add optional params when adding a product to the cart.
     *
     * @param {HTMLFormElement} form - The product form.
     */
    _getOptionalParams(form) {
        return {};
    }

    /**
     * Return the selected stored PTAVs in the provided form.
     *
     * @param {HTMLFormElement} form - The product form.
     *
     * @returns {Number[]} - The selected stored PTAVs, as a list of
     *     `product.template.attribute.value` ids.
     */
    _getSelectedPtavs(form) {
        const selectedPtavElements = form.querySelectorAll(
            'input.js_variant_change:not(.no_variant):checked, select.js_variant_change:not(.no_variant)'
        );
        return Array.from(selectedPtavElements).map(el => parseInt(el.value));
    }

    /**
     * Return the custom PTAV values in the provided form.
     *
     * @param {HTMLFormElement} form - The product form.
     *
     * @returns {{id: number, value: string}[]} - An array of objects where each object contains:
     *     - `custom_product_template_attribute_value_id`: The ID of the custom PTAV.
     *     - `custom_value`: The value assigned to the custom PTAV.
     */
    _getCustomPtavValues(form) {
        const customPtavValueElements = form.querySelectorAll('.variant_custom_value');
        return Array.from(customPtavValueElements).map(el => ({
            'custom_product_template_attribute_value_id': parseInt(
                el.dataset.customProductTemplateAttributeValueId
            ),
            'custom_value': el.value,
        }));
    }

    /**
     * Return the selected non-stored PTAVs in the provided form.
     *
     * @param {HTMLFormElement} form - The product form.
     *
     * @returns {Number[]} - The selected non-stored PTAVs, as a list of
     *     `product.template.attribute.value` ids.
     */
    _getSelectedNoVariantPtavs(form) {
        const selectedNoVariantPtavElements = form.querySelectorAll(
            'input.no_variant.js_variant_change:checked, select.no_variant.js_variant_change'
        );
        return Array.from(selectedNoVariantPtavElements).map(el => parseInt(el.value));
    }
}

registry.category('public.interactions').add('website_sale.add_to_cart', AddToCart);
