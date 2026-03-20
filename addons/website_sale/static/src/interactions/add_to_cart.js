import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';

export class AddToCart extends Interaction {
    static selector = '.oe_website_sale button[name="add_to_cart"]';
    dynamicContent = {
        _root: { "t-on-click.prevent": this.locked(this.addToCart, true) },
    };

    /**
     * Add a product to the cart.
     *
     * @param {MouseEvent} ev
     */
    async addToCart(ev) {
        const button = ev.currentTarget;

        const productEl = button.closest('.js_product');
        const productPageData = productEl ? {
            quantity: parseFloat(productEl.querySelector('input[name="add_qty"]')?.value) || 1,
            uomId: parseInt(productEl.querySelector('input[name="uom_id"]:checked')?.value),
            ptavs: this._getSelectedPtavs(productEl),
            productCustomAttributeValues: this._getCustomPtavValues(productEl),
            noVariantAttributeValues: this._getSelectedNoVariantPtavs(productEl),
        } : {};

        const productContainer = productEl ?? button.closest('#products_grid');
        const optionalParams = productContainer ? this._getOptionalParams(productContainer) : {};

        const quantity = await this.waitFor(this.services['cart'].add({
            productTemplateId: parseInt(button.dataset.productTemplateId),
            productId: parseInt(button.dataset.productId),
            isCombo: button.dataset.productType === 'combo',
            ptavs: JSON.parse(button.dataset.ptavIds || '[]'),
            ...productPageData,
            ...optionalParams,
        }, {
            isBuyNow: button.dataset.action === 'buy_now',
            isConfigured: button.parentElement.id === 'add_to_cart_wrap',
            showQuantity: button.dataset.showQuantity === 'True',
        }));

        if (quantity > 0) {
            button.dispatchEvent(new CustomEvent('product_added_to_cart', { bubbles: true }));
        }
        if (button.closest('.o_carousel_product_card')?.dataset?.add2cartRerender === 'True') {
            const dynamicSnippetProducts = button.closest('.s_dynamic_snippet_products');
            this.services['public.interactions'].stopInteractions(dynamicSnippetProducts);
            this.services['public.interactions'].startInteractions(dynamicSnippetProducts);
        }

        return quantity;
    }

    /**
     * Hook to add optional params when adding a product to the cart.
     *
     * @param {HTMLElement} el - The element containing the product.
     */
    _getOptionalParams(el) {
        return {};
    }

    /**
     * Return the selected stored PTAVs in the provided element.
     *
     * @param {HTMLElement} el - The element containing the product.
     *
     * @returns {Number[]} - The selected stored PTAVs, as a list of
     *     `product.template.attribute.value` ids.
     */
    _getSelectedPtavs(el) {
        const selectedPtavElements = el.querySelectorAll(
            'input.js_variant_change:not(.no_variant):checked, select.js_variant_change:not(.no_variant)'
        );
        return Array.from(selectedPtavElements).map(el => parseInt(el.value));
    }

    /**
     * Return the custom PTAV values in the provided element.
     *
     * @param {HTMLElement} el - The element containing the product.
     *
     * @returns {{id: number, value: string}[]} - An array of objects where each object contains:
     *     - `custom_product_template_attribute_value_id`: The ID of the custom PTAV.
     *     - `custom_value`: The value assigned to the custom PTAV.
     */
    _getCustomPtavValues(el) {
        const customPtavValueElements = el.querySelectorAll('.variant_custom_value');
        return Array.from(customPtavValueElements).map(el => ({
            'custom_product_template_attribute_value_id': parseInt(
                el.dataset.customProductTemplateAttributeValueId
            ),
            'custom_value': el.value,
        }));
    }

    /**
     * Return the selected non-stored PTAVs in the provided element.
     *
     * @param {HTMLElement} el - The element containing the product.
     *
     * @returns {Number[]} - The selected non-stored PTAVs, as a list of
     *     `product.template.attribute.value` ids.
     */
    _getSelectedNoVariantPtavs(el) {
        const selectedNoVariantPtavElements = el.querySelectorAll(
            'input.no_variant.js_variant_change:checked, select.no_variant.js_variant_change'
        );
        return Array.from(selectedNoVariantPtavElements).map(el => parseInt(el.value));
    }
}

registry.category('public.interactions').add('website_sale.add_to_cart', AddToCart);
