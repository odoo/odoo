/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { rpc } from "@web/core/network/rpc";
import { cartHandlerMixin } from '@website_sale/js/website_sale_utils';
import { WebsiteSale } from '@website_sale/js/website_sale';
import { _t } from "@web/core/l10n/translation";

publicWidget.registry.AddToCartSnippet = WebsiteSale.extend(cartHandlerMixin, {
    selector: '.s_add_to_cart_btn',
    events: {
        'click': '_onClickAddToCartButton',
    },

    init() {
        this._super(...arguments);
        this.notification = this.bindService("notification");
    },

    _onClickAddToCartButton: async function (ev) {
        const dataset = ev.currentTarget.dataset;

        const action = dataset.action;
        const productId = parseInt(dataset.productVariantId);
        const productTemplateId = parseInt(dataset.productTemplateId);
        const isCombo = dataset.isCombo === 'true';

        if (!productId || isCombo) {
            this.rootProduct = {
                product_id: productId,
                product_template_id: productTemplateId,
                quantity: 1,
                product_custom_attribute_values: [],
                variant_values: [],
                no_variant_attribute_values: [],
            };
            this._onProductReady();
        } else {
            const isAddToCartAllowed = await rpc(`/shop/product/is_add_to_cart_allowed`, {
                product_id: productId,
            });
            if (!isAddToCartAllowed) {
                this.notification.add(
                    _t('This product does not exist therefore it cannot be added to cart.'),
                    { title: 'User Error', type: 'warning' }
                );
                return;
            }
            this.isBuyNow = action === 'buy_now';
            this.stayOnPageOption = !this.isBuyNow;
            this.addToCart({product_id: productId, add_qty: 1});
        }
    },
});

export default publicWidget.registry.AddToCartSnippet;
