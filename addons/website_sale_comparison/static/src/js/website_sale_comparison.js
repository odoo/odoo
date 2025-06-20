import { EventBus } from '@odoo/owl';
import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { WarningDialog } from '@web/core/errors/error_dialogs';
import wSaleUtils from '@website_sale/js/website_sale_utils';
import comparisonUtils from '@website_sale_comparison/js/website_sale_comparison_utils';
import { ProductComparisonButton } from './product_comparison_button/product_comparison_button';

export class ProductComparison extends Interaction {
    static selector = '.js_sale';
    dynamicContent = {
        '.o_add_compare, .o_add_compare_dyn': { 't-on-click': this.addProduct },
        '.o_comparelist_remove': { 't-on-click': this.removeProduct },
        '.o_add_cart_form_compare': { 't-on-submit.prevent': this.submitForm },
    };

    setup() {
        this.bus = new EventBus();
        this.mountComponent(this.el, ProductComparisonButton, { bus: this.bus, currencyId: 1 }); // TODO(loti): use actual currency ID.
    }

    /**
     * @param {Event} ev
     */
    async addProduct(ev) {
        const el = ev.currentTarget;
        if (
            comparisonUtils.getComparisonProductIdsCookie().length
            >= comparisonUtils.MAX_COMPARISON_PRODUCTS
        ) {
            this.dialog.add(WarningDialog, {
                message: _t("You can only compare up to 4 products at a time."),
            });
            return;
        }
        let productId = el.dataset.productProductId;
        if (el.classList.contains('o_add_compare_dyn')) {
            productId = el.parentElement.querySelector('.product_id').value;
            if (!productId) { // Variants List View
                productId = el.parentElement.querySelector('input:checked').value;
            }
        }

        const form = el.closest('form') ?? this.el.querySelector('#product_details > form');
        if (!productId) {
            productId = await this.waitFor(rpc('/sale/create_product_variant', {
                product_template_id: form.querySelector('.product_template_id').value,
                product_template_attribute_value_ids:
                    wSaleUtils.getSelectedAttributeValues(form),
            }));
        }
        productId = parseInt(productId) || parseInt(el.dataset.productProductId);
        if (!productId) return;

        this.bus.trigger('comparison_add_product', { productId: productId });
        await wSaleUtils.animateClone(
            $('#comparelist .o_product_panel_header'),
            $(el).closest('form'),
            -50,
            10,
        );
    }

    /**
     * @param {Event} ev
     */
    removeProduct(ev) {
        const productId = parseInt(ev.currentTarget.dataset.productProductId);
        this.bus.trigger('comparison_remove_product', { productId: productId });

        const productIds = comparisonUtils.getComparisonProductIdsCookie();
        const comparisonUrl = `/shop/compare?products=${encodeURIComponent(productIds.join(','))}`;
        window.location.href = productIds.length ? comparisonUrl : '/shop';
    }

    /**
     * @param {Event} ev
     */
    submitForm(ev) {
        const form = ev.currentTarget;
        const productTemplateId = parseInt(
            form.querySelector('input[type="hidden"][name="product_template_id"]').value
        );
        const productId = parseInt(
            form.querySelector('input[type="hidden"][name="product_id"]').value
        );
        const showQuantity = Boolean(form.dataset.showQuantity);

         this.services['cart'].add({
            productTemplateId: productTemplateId,
            productId: productId,
        }, {
            showQuantity: showQuantity,
        });
    }
}

registry
    .category('public.interactions')
    .add('website_sale_comparison.product_comparison', ProductComparison);
