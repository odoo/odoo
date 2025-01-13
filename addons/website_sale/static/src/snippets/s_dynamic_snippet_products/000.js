import { rpc } from "@web/core/network/rpc";
import publicWidget from "@web/legacy/js/public/public_widget";
import DynamicSnippetCarousel from "@website/snippets/s_dynamic_snippet_carousel/000";

const DynamicSnippetProducts = DynamicSnippetCarousel.extend({
    selector: '.s_dynamic_snippet_products',

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Gets the category search domain
     *
     * @private
     */
    _getCategorySearchDomain() {
        const searchDomain = [];
        let productCategoryId = this.$el.get(0).dataset.productCategoryId;
        if (productCategoryId && productCategoryId !== 'all') {
            if (productCategoryId === 'current') {
                productCategoryId = undefined;
                const productCategoryField = $("#product_details").find(".product_category_id");
                if (productCategoryField && productCategoryField.length) {
                    productCategoryId = parseInt(productCategoryField[0].value);
                }
                if (!productCategoryId) {
                    this.trigger_up('main_object_request', {
                        callback: function (value) {
                            if (value.model === "product.public.category") {
                                productCategoryId = value.id;
                            }
                        },
                    });
                }
                if (!productCategoryId) {
                    // Try with categories from product, unfortunately the category hierarchy is not matched with this approach
                    const productTemplateId = $("#product_details").find(".product_template_id");
                    if (productTemplateId && productTemplateId.length) {
                        searchDomain.push(['public_categ_ids.product_tmpl_ids', '=', parseInt(productTemplateId[0].value)]);
                    }
                }
            }
            if (productCategoryId) {
                searchDomain.push(['public_categ_ids', 'child_of', parseInt(productCategoryId)]);
            }
        }
        return searchDomain;
    },
    /**
     * Gets the tag search domain
     *
     * @private
     */
    _getTagSearchDomain() {
        const searchDomain = [];
        let productTagIds = this.$el.get(0).dataset.productTagIds;
        productTagIds = productTagIds ? JSON.parse(productTagIds) : [];
        if (productTagIds.length) {
            searchDomain.push(['all_product_tag_ids', 'in', productTagIds.map(productTag => productTag.id)]);
        }
        return searchDomain;
    },
    /**
     * Method to be overridden in child components in order to provide a search
     * domain if needed.
     * @override
     * @private
     */
    _getSearchDomain: function () {
        const searchDomain = this._super.apply(this, arguments);
        searchDomain.push(...this._getCategorySearchDomain());
        searchDomain.push(...this._getTagSearchDomain());
        const productNames = this.$el.get(0).dataset.productNames;
        if (productNames) {
            const nameDomain = [];
            for (const productName of productNames.split(',')) {
                // Ignore empty names
                if (!productName.length) {
                    continue;
                }
                // Search on name, internal reference and barcode.
                if (nameDomain.length) {
                    nameDomain.unshift('|');
                }
                nameDomain.push(...[
                    '|', '|', ['name', 'ilike', productName],
                              ['default_code', '=', productName],
                              ['barcode', '=', productName],
                ]);
            }
            searchDomain.push(...nameDomain);
        }
        if (!this.el.dataset.showVariants) {
            searchDomain.push('hide_variants')
        }
        return searchDomain;
    },
    /**
     * @override
     */
    _getRpcParameters: function () {
        const productTemplateId = $("#product_details").find(".product_template_id");
        return Object.assign(this._super.apply(this, arguments), {
            productTemplateId: productTemplateId && productTemplateId.length ? productTemplateId[0].value : undefined,
        });
    },
    /**
     * @override
     * @private
     */
    _getMainPageUrl() {
        return "/shop";
    },
});

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

        await this.call('cart', 'add', {
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
publicWidget.registry.dynamic_snippet_products = DynamicSnippetProducts;

export default DynamicSnippetProducts;
