import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { rpc } from '@web/core/network/rpc';

export class CarouselProductCard extends Interaction {
    static selector = '.o_carousel_product_card';
    dynamicContent = {
        '.js_add_cart': { 't-on-click': this.onClickAddToCart },
        '.js_remove': { 't-on-click': this.onRemoveFromRecentlyViewed },
    };

    setup() {
        this.add2cartRerender = this.el.dataset.add2cartRerender === 'True';
    }

    /**
     * Event triggered by a click on the Add to cart button
     *
     * @param {Event} ev
     */
    async onClickAddToCart(ev) {
        const dataset = ev.currentTarget.dataset;

        const productTemplateId = parseInt(dataset.productTemplateId);
        const productId = parseInt(dataset.productId);
        const isCombo = dataset.productType === 'combo';
        const showQuantity = Boolean(dataset.showQuantity);

        await this.waitFor(this.services['cart'].add({
            productTemplateId: productTemplateId,
            productId: productId,
            isCombo: isCombo,
        }, {
            showQuantity: showQuantity,
        }));
        if (this.add2cartRerender) {
            const dynamicSnippetProducts = this.el.closest('.s_dynamic_snippet_products');
            this.services['public.interactions'].stopInteractions(dynamicSnippetProducts);
            this.services['public.interactions'].startInteractions(dynamicSnippetProducts);
        }
    }

    /**
     * Event triggered by a click on the remove button on a "recently viewed"
     * template.
     *
     * @param {Event} ev
     */
    async onRemoveFromRecentlyViewed(ev) {
        const rpcParams = {}
        if (ev.currentTarget.dataset.productSelected) {
            rpcParams.product_id = ev.currentTarget.dataset.productId;
        } else {
            rpcParams.product_template_id = ev.currentTarget.dataset.productTemplateId;
        }
        await this.waitFor(rpc('/shop/products/recently_viewed_delete', rpcParams));
        const dynamicSnippetProducts = this.el.closest('.s_dynamic_snippet_products');
        this.services['public.interactions'].stopInteractions(dynamicSnippetProducts);
        this.services['public.interactions'].startInteractions(dynamicSnippetProducts);
    }
}

registry
    .category('public.interactions')
    .add('website_sale.carousel_product_card', CarouselProductCard);
