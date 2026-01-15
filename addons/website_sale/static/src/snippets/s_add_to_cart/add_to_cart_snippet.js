import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';

export class AddToCartSnippet extends Interaction {
    static selector = '.s_add_to_cart_btn';
    dynamicContent = {
        _root: { 't-on-click': this.onClickAddToCartButton },
    };

    async onClickAddToCartButton(ev) {
        const dataset = ev.currentTarget.dataset;

        const productTemplateId = parseInt(dataset.productTemplateId);
        const productId = parseInt(dataset.productVariantId);
        const isCombo = dataset.productType === 'combo';
        const showQuantity = Boolean(dataset.showQuantity);
        const action = dataset.action;

        if (productId) {
            const isAddToCartAllowed = await this.waitFor(rpc(
                '/shop/product/is_add_to_cart_allowed', { product_id: productId }
            ));
            if (!isAddToCartAllowed) {
                this.services.notification.add(
                    _t("This product does not exist therefore it cannot be added to cart."),
                    { title: _t("User Error"), type: 'warning' }
                );
                return;
            }
        }

        this.services['cart'].add({
            productTemplateId: productTemplateId,
            productId: productId,
            isCombo: isCombo,
        }, {
            isBuyNow: action === 'buy_now',
            showQuantity: showQuantity,
        });
    }
}

registry
    .category('public.interactions')
    .add('website_sale.add_to_cart_snippet', AddToCartSnippet);
