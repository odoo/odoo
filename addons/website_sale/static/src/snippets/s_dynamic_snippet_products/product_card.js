import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

const DynamicSnippetProductsCard = publicWidget.Widget.extend({
    selector: '.o_carousel_product_card',
    read_events: {
        'click .js_add_cart': '_onClickAddToCart',
        'click .js_remove': '_onRemoveFromRecentlyViewed',
    },

    init(root, options) {
        const parent = options.parent || root;
        this._super(parent, options);
    },

    start() {
        this.add2cartRerender = this.el.dataset.add2cartRerender === 'True';
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Event triggered by a click on the Add to cart button
     *
     * @param {OdooEvent} ev
     */
    async _onClickAddToCart(ev) {
        const dataset = ev.currentTarget.dataset;

        const productTemplateId = parseInt(dataset.productTemplateId);
        const productId = parseInt(dataset.productId);
        const isCombo = dataset.productType === 'combo';

        await this.call('websiteSale', 'addToCart', {
            productTemplateId: productTemplateId,
            productId: productId,
            isCombo: isCombo,
        });
        if (this.add2cartRerender) {
            this.trigger_up('widgets_start_request', {
                $target: this.$el.closest('.s_dynamic'),
            });
        }
    },
    /**
     * Event triggered by a click on the remove button on a "recently viewed"
     * template.
     *
     * @param {OdooEvent} ev
     */
    async _onRemoveFromRecentlyViewed(ev) {
        const rpcParams = {}
        if (ev.currentTarget.dataset.productSelected) {
            rpcParams.product_id = ev.currentTarget.dataset.productId;
        } else {
            rpcParams.product_template_id = ev.currentTarget.dataset.productTemplateId;
        }
        await rpc("/shop/products/recently_viewed_delete", rpcParams);
        this.trigger_up('widgets_start_request', {
            $target: this.$el.closest('.s_dynamic'),
        });
    },
});

publicWidget.registry.dynamic_snippet_products_cta = DynamicSnippetProductsCard;
