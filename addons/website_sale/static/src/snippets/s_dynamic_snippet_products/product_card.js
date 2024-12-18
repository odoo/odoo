import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import wSaleUtils from "@website_sale/js/website_sale_utils";
import { WebsiteSale } from "../../js/website_sale";

const DynamicSnippetProductsCard = WebsiteSale.extend({
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
        const button = ev.currentTarget
        if (!button.dataset.productSelected || button.dataset.isCombo) {
            const dummy_form = document.createElement('form');
            dummy_form.setAttribute('method', 'post');
            dummy_form.setAttribute('action', '/shop/cart/update');

            const inputPT = document.createElement('input');
            inputPT.setAttribute('name', 'product_template_id');
            inputPT.setAttribute('type', 'hidden');
            inputPT.setAttribute('value', button.dataset.productTemplateId);
            dummy_form.appendChild(inputPT);

            const inputPP = document.createElement('input');
            inputPP.setAttribute('name', 'product_id');
            inputPP.setAttribute('type', 'hidden');
            inputPP.setAttribute('value', button.dataset.productId);
            dummy_form.appendChild(inputPP);

            return this._handleAdd($(dummy_form));  // existing logic expects jquery form
        }
        else {
            const data = await rpc("/shop/cart/update_json", {
                product_id: parseInt(ev.currentTarget.dataset.productId),
                add_qty: 1,
                display: false,
            });
            wSaleUtils.updateCartNavBar(data);
            wSaleUtils.showCartNotification(this.call.bind(this), data.notification_info);
        }
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
