import { EventBus } from '@odoo/owl';
import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { redirect } from '@web/core/utils/urls';
import wSaleUtils from '@website_sale/js/website_sale_utils';
import comparisonUtils from '@website_sale_comparison/js/website_sale_comparison_utils';
import {
    ProductComparisonBottomBar
} from '@website_sale_comparison/js/product_comparison_bottom_bar/product_comparison_bottom_bar';

export class ProductComparison extends Interaction {
    static selector = '.js_sale';
    dynamicContent = {
        '.o_add_compare, .o_add_compare_dyn': { 't-on-click': this.addProduct },
        'input.product_id': { 't-on-change': this.onChangeVariant },
        '.o_comparelist_remove': { 't-on-click': this.removeProduct },
        'button[name="comparison_add_to_cart"]': { 't-on-click': this.addToCart },
    };

    setup() {
        this.bus = new EventBus();
        this.mountComponent(document.body, ProductComparisonBottomBar, { bus: this.bus });
        this.position = 0;
        
        // Mini sticky comparison elements
        this.miniStickyEl = null;
        this.mainScrollEl = null;
        this.miniScrollEl = null;
    }

    start() {
        this._adaptToHeaderChange();
        this.registerCleanup(this.services.website_menus.registerCallback(this._adaptToHeaderChange.bind(this)));
        
        // Initialize mini sticky comparison if on comparison page
        if (this.el.querySelector('#o_comparelist_table')) {
            this._initMiniStickyComparison();
        }
    }

    /**
     * Add a product to the comparison.
     *
     * @param {Event} ev
     */
    async addProduct(ev) {
        if (this._checkMaxComparisonProducts()) return;

        const el = ev.currentTarget;
        let productId = parseInt(el.dataset.productProductId);
        const form = el.closest('form');
        if (!productId) {
            productId = await this.waitFor(rpc('/sale/create_product_variant', {
                product_template_id: parseInt(el.dataset.productTemplateId),
                product_template_attribute_value_ids: wSaleUtils.getSelectedAttributeValues(form),
            }));
        }
        if (!productId || this._checkProductAlreadyInComparison(productId)) {
            this._updateDisabled(el, true);
            return;
        }

        comparisonUtils.addComparisonProduct(productId);
        this.bus.dispatchEvent(new CustomEvent('comparison_products_changed', { bubbles: true }));
        this._updateDisabled(el, true);
        await wSaleUtils.animateClone(
            $('.o_comparison_bottom_bar'),
            $(this.el.querySelector('#product_detail_main') ?? form),
            -50,
            10,
        );
    }

    /**
     * Enable/disable the "add to comparison" button based on the selected variant.
     *
     * @param {Event} ev
     */
    onChangeVariant(ev) {
        const input = ev.target;
        const productId = input.value;
        const button = input.closest('.js_product')?.querySelector('[data-action="o_comparelist"]');
        if (button) {
            const isDisabled = comparisonUtils.getComparisonProductIds().includes(
                parseInt(productId)
            );
            this._updateDisabled(button, isDisabled);
            button.dataset.productProductId = productId;
        }
    }

    /**
     * Remove a product from the comparison.
     *
     * @param {Event} ev
     */
    removeProduct(ev) {
        const productId = parseInt(ev.currentTarget.dataset.productProductId);
        comparisonUtils.removeComparisonProduct(productId);
        this.bus.dispatchEvent(new CustomEvent('comparison_products_changed', { bubbles: true }));

        const productIds = comparisonUtils.getComparisonProductIds();
        const comparisonUrl = `/shop/compare?products=${encodeURIComponent(productIds.join(','))}`;
        redirect(productIds.length ? comparisonUrl : '/shop');
    }

    /**
     * Add a product to the cart from the comparison page.
     *
     * @param {Event} ev
     */
    addToCart(ev) {
        const button = ev.currentTarget;
        const productId = parseInt(button.dataset.productProductId);
        const productTemplateId = parseInt(button.dataset.productTemplateId);
        const showQuantity = Boolean(button.dataset.showQuantity);

         this.services['cart'].add({
            productTemplateId: productTemplateId,
            productId: productId,
        }, {
            showQuantity: showQuantity,
        });
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adapt sticky positioning to header height changes.
     *
     * @private
     */
    _adaptToHeaderChange() {
        let position = 0;
        
        // Calculate total height of fixed elements at top
        for (const el of this.el.ownerDocument.querySelectorAll(".o_top_fixed_element")) {
            position += el.offsetHeight;
        }

        if (this.position !== position) {
            this.position = position;
            this.updateContent();
            
            // Update mini sticky position if it exists
            if (this.miniStickyEl) {
                this.miniStickyEl.style.top = `${position}px`;
            }
        }
    }

    /**
     * Initialize the mini sticky comparison overview.
     *
     * @private
     */
    _initMiniStickyComparison() {
        this.miniStickyEl = this.el.querySelector('#miniStickyComparison');
        const productImagesEl = this.el.querySelector('#o_comparelist_table ul:first-of-type');
        
        if (!this.miniStickyEl || !productImagesEl) return;
        
        // Set initial position
        this.miniStickyEl.style.top = `${this.position}px`;
        
        // Get scroll containers
        this.mainScrollEl = this.el.querySelector('.table-comparator').closest('.overflow-x-auto');
        this.miniScrollEl = this.miniStickyEl.querySelector('.overflow-x-auto');
        
        // Handle vertical scroll (show/hide mini sticky)
        const handleVerticalScroll = () => {
            const rect = productImagesEl.getBoundingClientRect();
            const shouldShow = rect.bottom < this.position + 20;
            
            this.miniStickyEl.classList.toggle('show', shouldShow);
            this.miniStickyEl.classList.toggle('d-none', !shouldShow);
            
            // Sync horizontal position when showing
            if (shouldShow && this.mainScrollEl && this.miniScrollEl) {
                this.miniScrollEl.scrollLeft = this.mainScrollEl.scrollLeft;
            }
        };
        
        // Handle horizontal scroll sync
        const syncScroll = (source, target) => {
            if (!source._syncing) {
                target._syncing = true;
                target.scrollLeft = source.scrollLeft;
                requestAnimationFrame(() => target._syncing = false);
            }
        };
        
        // Bind events
        window.addEventListener('scroll', handleVerticalScroll, { passive: true });
        if (this.mainScrollEl && this.miniScrollEl) {
            this.mainScrollEl.addEventListener('scroll', () => syncScroll(this.mainScrollEl, this.miniScrollEl), { passive: true });
            this.miniScrollEl.addEventListener('scroll', () => syncScroll(this.miniScrollEl, this.mainScrollEl), { passive: true });
        }
        
        // Cleanup
        this.registerCleanup(() => {
            window.removeEventListener('scroll', handleVerticalScroll);
        });
        
        // Initial check
        handleVerticalScroll();
    }

    /**
     * Check whether the maximum number of products in the comparison has been reached, and if so,
     * show a warning.
     *
     * @return {boolean} Whether the maximum number of products in the comparison has been reached.
     */
    _checkMaxComparisonProducts() {
        if (
            comparisonUtils.getComparisonProductIds().length
            >= comparisonUtils.MAX_COMPARISON_PRODUCTS
        ) {
            this.services.notification.add(
                _t("You can compare up to 4 products at a time."),
                {
                    type: 'warning',
                    sticky: false,
                    title: _t("Too many products to compare"),
                },
            );
            return true;
        }
        return false;
    }

    /**
     * Check whether the product is already in the comparison, and if so, show a warning.
     *
     * @param productId The ID of the product to check.
     * @return {boolean} Whether the product is already in the comparison.
     */
    _checkProductAlreadyInComparison(productId) {
        if (comparisonUtils.getComparisonProductIds().includes(productId)) {
            this.services.notification.add(
                _t("This product has already been added to the comparison."),
                { type: 'warning', sticky: false },
            );
            return true;
        }
        return false;
    }

    _updateDisabled(el, isDisabled) {
        el.disabled = isDisabled;
        el.classList.toggle('disabled', isDisabled);
    }
}

registry
    .category('public.interactions')
    .add('website_sale_comparison.product_comparison', ProductComparison);
