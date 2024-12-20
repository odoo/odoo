import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class Product extends Interaction {
    static selector = "#product_detail_main";
    dynamicContent = {
        "#add_to_cart, .o_we_buy_now": {
            "t-on-click": this.addToCart,
        },
    };

    addToCart(ev) {
        const isBuyNow = ev.currentTarget.classList.contains('o_we_buy_now'); // TODO VCR Use dataset instead?
        this.services.websiteSale.addToCart(
        //    this.product, this.options,  // TODO VCR
            this.getProductInformation(ev), { isBuyNow: isBuyNow, isConfigured: true },
        );
    }

    /**
     * Hook to append additional product information in overriding modules.
     *
     * Override this to
     *
     * @return {Object} The additional RPC params.
     */
    getProductInformation(ev) {
        const dataset = ev.target.dataset;
        const productId = parseInt(this.el.querySelector([
            'input[type="hidden"][name="product_id"]',
            // Variants list view
            'input[type="radio"][name="product_id"]:checked',
        ].join(','))?.value);
        const quantity = parseFloat(this.el.querySelector('input[name="add_qty"]')?.value);
        return {
            productTemplateId: parseInt(dataset.productTemplateId),
            productId: productId,
            quantity: quantity,
            ptavs: this._getSelectedPTAV(this.el),
            productCustomAttributeValues: this._getCustomPTAVValues(this.el),
            noVariantAttributeValues: this._getSelectedNoVariantPTAV(this.el),
            isCombo: dataset.productType === 'combo',
        };
    }

    /**
     * Return the selected stored PTAV(s) of in the provided element.
     *
     * @private
     * @param {HTMLDivElement} element - The div in which the product is.
     *
     * @returns {Number[]} - The selected stored attribute(s), as a list of
     *      `product.template.attribute.value` ids.
     */
    _getSelectedPTAV(element) {
        // Variants list view
        let combination = element.querySelector('input.js_product_change:checked')?.dataset.combination;
        if (combination) {
            return JSON.parse(combination);
        }

        const selectedPTAVElements = element.querySelectorAll([
            '.js_product input.js_variant_change:not(.no_variant):checked',
            '.js_product select.js_variant_change:not(.no_variant)'
        ].join(','));
        let selectedPTAV = [];
        for(const el of selectedPTAVElements) {
            selectedPTAV.push(parseInt(el.value));
        }
        return selectedPTAV;
    }

    /**
     * Return the custom PTAV(s) values in the provided element.
     *
     * @private
     * @param {HTMLDivElement} element - The div in which the product is.
     *
     * @returns {{id: number, value: string}[]} An array of objects where each object contains:
     *      - `custom_product_template_attribute_value_id`: The ID of the custom attribute.
     *      - `custom_value`: The value assigned to the custom attribute.
     */
    _getCustomPTAVValues(element) {
        const customPTAVsValuesElements = element.querySelectorAll('.variant_custom_value');
        let customPTAVsValues = [];
        for(const el of customPTAVsValuesElements) {
            customPTAVsValues.push({
                'custom_product_template_attribute_value_id': parseInt(
                    el.dataset.custom_product_template_attribute_value_id
                ),
                'custom_value': el.value,
            });
        }
        return customPTAVsValues;
    }

    /**
     * Return the selected non-stored PTAV(s) of the product in the provided element.
     *
     * @private
     * @param {HTMLDivElement} element - The element in which the product is.
     *
     * @returns {Number[]} - The selected non-stored attribute(s), as a list of
     *      `product.template.attribute.value` ids.
     */
    _getSelectedNoVariantPTAV(element) {
        const selectedNoVariantPTAVElements = element.querySelectorAll([
            'input.no_variant.js_variant_change:checked',
            'select.no_variant.js_variant_change',
        ].join(','));
        let selectedNoVariantPTAV = [];
        for(const el of selectedNoVariantPTAVElements) {
            selectedNoVariantPTAV.push(parseInt(el.value));
        }
        return selectedNoVariantPTAV;
    }


}

registry.category("public.interactions").add("website_sale.product", Product);
