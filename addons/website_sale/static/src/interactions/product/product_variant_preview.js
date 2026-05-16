import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';

export class ProductVariantPreview extends Interaction {
    static selector = "#o_wsale_products_grid";

    dynamicContent = {
        _window: {
            "t-on-resize": this.debounced(this.updateVariantPreview, 250),
        },
    };

    setup() {
        // Class `gap-1` on parent adds 4px margin for each ptav.
        this.margin = 4;
        this.updateVariantPreview();
    }

    /**
     * Hide all attribute values from view to be able to recompute correctly how many elements are
     * to be shown.
     *
     * @private
     *
     * @returns {void}
     */
    _resetDisplay(attributePreviewer) {
        for (const child of attributePreviewer.children) {
            child.classList.add('d-none');
        }
    }

    /**
     * Update the count of hidden PTAVs with the correct number and make it visible.
     *
     * @private
     * @param {Element} currentPTAV
     * @param {Number} remainingSpace
     *
     * @returns {void}
     */
    _showHiddenPTAVsElement(
        attributePreviewerValues, currentPTAV, remainingSpace, displayedPTAVCount
    ) {
        const {
            ptavCount,
            offsetWidthPTAVS,
            hiddenCountSpan,
            hiddenCountSpanWidth,
        } = attributePreviewerValues;
        while (currentPTAV && hiddenCountSpanWidth >= remainingSpace) {
            currentPTAV.classList.add("d-none");
            displayedPTAVCount--;
            remainingSpace += offsetWidthPTAVS.get(currentPTAV);
            currentPTAV = currentPTAV.previousElementSibling;
        }
        const hiddenPTAVCount = ptavCount - displayedPTAVCount;
        hiddenCountSpan.firstElementChild.textContent = `+${hiddenPTAVCount}`;
        hiddenCountSpan.classList.remove("d-none");
    }

    /**
     * For each ptav check if there is enough space to add on the parent element and update the
     * hidden PTAVs count accordingly, with the truncated elements from the backend.
     *
     * @private
     *
     * @returns {void}
     */
    _updateVariantPreview(attributePreviewer, attributePreviewerValues) {
        const { containerWidth, ptavs, ptavCount, offsetWidthPTAVS } = attributePreviewerValues;
        this._resetDisplay(attributePreviewer);
        let usedWidth = 0;
        let displayedPTAVCount = 0;
        for (const ptav of ptavs) {
            ptav.classList.remove('d-none');
            usedWidth += offsetWidthPTAVS.get(ptav) + this.margin;
            displayedPTAVCount++;
            const remainingSpace = containerWidth - usedWidth;
            const isLastPTAV = ptav === ptavs[ptavs.length - 1];
            const hasHiddenPtavs = isLastPTAV && ptavCount > displayedPTAVCount;
            if (usedWidth >= containerWidth || hasHiddenPtavs) {
                this._showHiddenPTAVsElement(
                    attributePreviewerValues, ptav, remainingSpace, displayedPTAVCount,
                );
                break;
            }
        }
    }

    /**
     * Triggered on the parent element of the '.o_wsale_attribute_previewer' elements to run the
     * interaction once instead of multiple times depending on how many elements or products exist
     * on the page.
     *
     * Schedules and batches updates for all active '.o_wsale_attribute_previewer' elements
     * to refresh their variant previews efficiently.
     *
     * Uses `requestAnimationFrame` to ensure that updates occur in sync with the browser’s
     * rendering cycle, preventing redundant or frequent recalculations (trigger by offsetWidth).
     */
    updateVariantPreview() {
        const attributePreviewers = this.el.querySelectorAll(".o_wsale_attribute_previewer");
        const updateAllVariantPreview = this.protectSyncAfterAsync(() => {
            const attributePreviewerValues = new Map();

            // ---- Phase 1: Initiate the values needed for each attribute previewer ---------------
            // Split into two sub-loops to avoid a forced reflow per product:
            
            // ---- Phase 1a: all DOM writes (resetDisplay, textContent, classList) ----------------
            for (const attributePreviewer of attributePreviewers) {
                this._resetDisplay(attributePreviewer);
                const ptavs = attributePreviewer.querySelectorAll(".o_product_variant_preview");
                // Set the hiddenCountSpan to the maximum number of ptavs there is to assume
                // the worst case space it needs.
                const hiddenCountSpan = attributePreviewer.querySelector(
                    "span[name='hidden_ptavs_count']");
                const ptavCount = ptavs.length + Number(
                    attributePreviewer.dataset.hiddenPtavCount ?? 0);
                hiddenCountSpan.firstElementChild.textContent = `+${ptavCount}`;
                hiddenCountSpan.classList.remove("d-none");
                attributePreviewerValues.set(
                    attributePreviewer,
                    {
                        ptavs,
                        hiddenCountSpan,
                        ptavCount,
                        offsetWidthPTAVS: new Map(),
                        hiddenCountSpanWidth: 0,
                    },
                );
            }

            // ---- Phase 1b: all reads (single reflow for all products) ----------------
            // All writes above are now complete so offsetWidth flushes layout only once,
            // regardless of how many products are on the page.
            for (const attributePreviewer of attributePreviewers) {
                const currentValues = attributePreviewerValues.get(attributePreviewer)
                currentValues.containerWidth = attributePreviewer.offsetWidth;
            }

            // ---- Phase 2: Display all PTAVs to get the correct width (pure writes) --------------
            for (const attributePreviewer of attributePreviewers) {
                const currentValues = attributePreviewerValues.get(attributePreviewer);
                for (const ptav of currentValues.ptavs) {
                    ptav.classList.remove("d-none");
                }
            }

            // ---- Phase 3: bulk offsetWidth reads ------------------------------------------------
            // A recalculation of the styles is triggered every time offsetWidth is called.
            // Get all offsetWidths in one step to avoid recalculation for each element separately.
            for (const attributePreviewer of attributePreviewers) {
                const currentValues = attributePreviewerValues.get(attributePreviewer);
                for (const ptav of currentValues.ptavs) {
                    currentValues.offsetWidthPTAVS.set(ptav, ptav.offsetWidth);
                }
                currentValues.hiddenCountSpanWidth = (
                    currentValues.hiddenCountSpan.offsetWidth + this.margin * 2
                );
            }

            // ---- Phase 4: apply display logic (pure writes) -------------------------------------
            for (const attributePreviewer of attributePreviewers) {
                this._updateVariantPreview(
                    attributePreviewer, attributePreviewerValues.get(attributePreviewer)
                );
            }
        });
        requestAnimationFrame(updateAllVariantPreview);
    }
}

registry
    .category('public.interactions')
    .add('website_sale.product_variant_preview', ProductVariantPreview);

registry
    .category("public.interactions.edit")
    .add("website.product_variant_preview", { Interaction: ProductVariantPreview });
