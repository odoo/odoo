import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import wSaleUtils from '@website_sale/js/website_sale_utils';

export class AddToCart extends Interaction {
    static selector = '#add_to_cart, .o_we_buy_now, #products_grid .o_wsale_product_btn .a-submit';
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
        this._updateRootProduct(form);
        const isBuyNow = el.classList.contains('o_we_buy_now');
        const isConfigured = el.parentElement.id === 'add_to_cart_wrap';
        const showQuantity = Boolean(el.dataset.showQuantity);
        return this.services['cart'].add(this.rootProduct, {
            isBuyNow: isBuyNow,
            isConfigured: isConfigured,
            showQuantity: showQuantity,
        });
    }

    /**
     * Update the root product based on the info in the provided form.
     *
     * @param {HTMLFormElement} form - The product form.
     */
    _updateRootProduct(form) {
        const productId = parseInt(
            form.querySelector('input[type="hidden"][name="product_id"]')?.value
        );
        const productEl = form.closest('.js_product') ?? form;
        const quantity = parseFloat(productEl.querySelector('input[name="add_qty"]')?.value);
        const uomId = this._getUoMId(form);
        const isCombo = form.querySelector(
            'input[type="hidden"][name="product_type"]'
        )?.value === 'combo';
        this.rootProduct = {
            ...(productId ? { productId: productId } : {}),
            productTemplateId: parseInt(form.querySelector(
                'input[type="hidden"][name="product_template_id"]',
            ).value),
            ...(quantity ? { quantity: quantity } : {}),
            ...(uomId ? { uomId: uomId } : {}),
            ptavs: this._getSelectedPtavs(form),
            productCustomAttributeValues: this._getCustomPtavValues(form),
            noVariantAttributeValues: this._getSelectedNoVariantPtavs(form),
            ...(isCombo ? { isCombo: isCombo } : {}),
        };
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

    _getUoMId(element) {
        return parseInt(element.querySelector('input[name="uom_id"]:checked')?.value)
    }
}

registry.category('public.interactions').add('website_sale.add_to_cart', AddToCart);
