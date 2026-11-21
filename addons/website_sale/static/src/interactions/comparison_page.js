import { registry } from '@web/core/registry';
import comparisonUtils from '@website_sale/js/comparison_utils';
import { redirect } from '@web/core/utils/urls';
import { BelowTopFixedElements } from "@website/interactions/below_top_fixed_elements";

export class ComparisonPage extends BelowTopFixedElements {
    static selector = '.o_wsale_comparison_page';
    dynamicContent = {
        ...this.dynamicContent,
        _stickyEl: {
            ...this.dynamicContent._stickyEl,
            // Managed here (and not with `classList`) so that the mini sticky
            // is hidden again when the interaction stops (e.g. in edit mode),
            // together with the reset of its `top`.
            "t-att-class": () => ({
                show: this.isMiniStickyShown,
                "d-none": !this.isMiniStickyShown,
            }),
        },
        '.o_comparelist_remove': { 't-on-click': this.removeProduct },
        'button[name="comparison_clear_all_button"]': { 't-on-click': this.clearAllProducts },
    };

    gap = 0;

    setup() {
        super.setup();
        this.stickyEl = this.el.querySelector("#miniStickyComparison");
        this.isMiniStickyShown = false;
    }

    start() {
        super.start();
        this._initMiniStickyComparison();
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

        // Get scroll containers
        const mainScrollEl = this.el.querySelector('.table-comparator').closest('.overflow-x-auto');
        const miniScrollEl = this.el.querySelector('#miniStickyComparison .overflow-x-auto');

        // Handle vertical scroll (show/hide mini sticky)
        const handleVerticalScroll = () => {
            const rect = productImagesEl.getBoundingClientRect();
            const shouldShow = rect.bottom < this.topFixedOffset + 20;

            if (this.isMiniStickyShown !== shouldShow) {
                this.isMiniStickyShown = shouldShow;
                this.updateContent();
            }

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
    .add('website_sale.comparison_page', ComparisonPage);
