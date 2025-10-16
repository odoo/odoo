import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import comparisonUtils from '@website_sale_comparison/js/website_sale_comparison_utils';
import { redirect } from '@web/core/utils/urls';

export class ComparisonPage extends Interaction {
    static selector = '.o_wsale_comparison_page';
    dynamicContent = {
        '.o_comparelist_remove': { 't-on-click': this.removeProduct },
        'button[name="comparison_clear_all_button"]': { 't-on-click': this.clearAllProducts },
    };

    // TODO the sticky logic could probably make use of the WebsiteSaleStickyObject
    // interaction. We'd simply need to remove the offset that comes with the interaction
    // and handle the fact that the sticky element is hidden and appears when the user scrolls.

    setup() {
        this.position = 0;
    }

    start() {
        this._adaptToHeaderChange();
        this.registerCleanup(this.services.website_menus.registerCallback(this._adaptToHeaderChange.bind(this)));
        this._initMiniStickyComparison();
    }

    /**
     * Adapt the position of elements when the header changes.
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
            const miniStickyEl = this.el.querySelector('#miniStickyComparison');
            if (miniStickyEl) {
                miniStickyEl.style.top = `${position}px`;
            }
        }
    }

    /**
     * Clear all products from the comparison.
     */
    clearAllProducts() {
        comparisonUtils.clearComparisonProducts(this.env.bus);
        redirect('/shop');
    }

    /**
     * Initialize the mini sticky comparison overview.
     *
     * @private
     */
    _initMiniStickyComparison() {
        const miniStickyEl = this.el.querySelector('#miniStickyComparison');
        const productImagesEl = this.el.querySelector('#o_comparelist_table ul:first-of-type');

        if (!miniStickyEl || !productImagesEl) return;

        // Set initial position
        miniStickyEl.style.top = `${this.position}px`;

        // Get scroll containers
        const mainScrollEl = this.el.querySelector('.table-comparator').closest('.overflow-x-auto');
        const miniScrollEl = this.el.querySelector('#miniStickyComparison .overflow-x-auto');

        // Handle vertical scroll (show/hide mini sticky)
        const handleVerticalScroll = () => {
            const rect = productImagesEl.getBoundingClientRect();
            const shouldShow = rect.bottom < this.position + 20;

            miniStickyEl.classList.toggle('show', shouldShow);
            miniStickyEl.classList.toggle('d-none', !shouldShow);

            // Sync horizontal position when showing
            if (shouldShow && mainScrollEl && miniScrollEl) {
                miniScrollEl.scrollLeft = mainScrollEl.scrollLeft;
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
        this.registerCleanup(
            () => window.removeEventListener('scroll', handleVerticalScroll, { passive: true })
        );
        if (mainScrollEl && miniScrollEl) {
            const syncMainToMiniScroll = (_) => syncScroll(mainScrollEl, miniScrollEl);
            const syncMiniToMainScroll = (_) => syncScroll(miniScrollEl, mainScrollEl);
            mainScrollEl.addEventListener('scroll', syncMainToMiniScroll, { passive: true });
            miniScrollEl.addEventListener('scroll', syncMiniToMainScroll, { passive: true });
            this.registerCleanup(() => mainScrollEl.removeEventListener(
                'scroll', syncMainToMiniScroll, { passive: true }
            ));
            this.registerCleanup(() => miniScrollEl.removeEventListener(
                'scroll', syncMiniToMainScroll, { passive: true }
            ));
        }

        // Initial check
        handleVerticalScroll();
    }

    /**
     * Remove a product from the comparison.
     *
     * @param {Event} ev
     */
    removeProduct(ev) {
        const productId = parseInt(ev.currentTarget.dataset.productId);
        comparisonUtils.removeComparisonProduct(productId, null); // No bus needed on comparison page

        const productIds = comparisonUtils.getComparisonProductIds();
        if (productIds.length === 0) {
            redirect('/shop');
        } else {
            const comparisonUrl = `/shop/compare?products=${encodeURIComponent(productIds.join(','))}`;
            redirect(comparisonUrl);
        }
    }
}

registry
    .category('public.interactions')
    .add('website_sale_comparison.comparison_page', ComparisonPage);
