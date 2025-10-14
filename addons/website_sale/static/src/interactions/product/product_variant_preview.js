import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class ProductVariantPreview extends Interaction {
    static selector = ".o_wsale_attribute_previewer";
    static instances = [];
    static currentFrame = null;

    dynamicContent = {
        _window: {
            "t-on-resize": this.debounced(this.updateVariantPreview, 250),
        },
    };

    setup() {
        this.ptavs = this.el.querySelectorAll(".o_product_variant_preview");
        this.hiddenCountSpan = this.el.querySelector('span[name="hidden_ptavs_count"]');
        this.ptavCount = this.ptavs.length + Number(this.el.dataset.hiddenPtavCount ?? 0);
        this.displayedPTAVCount = 0;
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
    _resetDisplay() {
        for (const child of this.el.children) {
            child.classList.add("d-none");
        }
    }

    /**
     * Updates the span to include the correct number of hidden PTAVs and return the
     * new width of the element.
     *
     * @returns {Number}
     */
    _updateAndGetHiddenPTAVsWidth(PTAVWidth) {
        const hiddenPTAVCount = this.ptavCount - this.displayedPTAVCount;
        this.hiddenCountSpan.firstElementChild.textContent = `+${hiddenPTAVCount}`;
        return PTAVWidth + this.margin * 2;
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
    _showHiddenPTAVsElement(currentPTAV, remainingSpace, PTAVWidth) {
        this.hiddenCountSpan.classList.remove("d-none");
        let hiddenCountSpanWidth = this._updateAndGetHiddenPTAVsWidth(PTAVWidth);
        while (currentPTAV && hiddenCountSpanWidth >= remainingSpace) {
            currentPTAV.classList.add("d-none");
            this.displayedPTAVCount--;
            hiddenCountSpanWidth = this._updateAndGetHiddenPTAVsWidth(PTAVWidth);
            remainingSpace += PTAVWidth;
            currentPTAV = currentPTAV.previousElementSibling;
        }
    }

    /**
     * For each ptav check if there is enough space to add on the parent element and update the
     * hidden PTAVs count accordingly, with the truncated elements from the backend.
     *
     * @private
     *
     * @returns {void}
     */
    _updateVariantPreview(containerWidth, PTAVWidth) {
        let usedWidth = 0;
        this.displayedPTAVCount = 0;
        this._resetDisplay();
        for (const ptav of this.ptavs) {
            ptav.classList.remove("d-none");
            usedWidth += PTAVWidth + this.margin;
            this.displayedPTAVCount++;
            const remainingSpace = containerWidth - usedWidth;
            const isLastPTAV = ptav === this.ptavs[this.ptavs.length - 1];
            const hasHiddenPtavs = isLastPTAV && this.ptavCount > this.displayedPTAVCount;
            if (usedWidth >= containerWidth || hasHiddenPtavs) {
                this._showHiddenPTAVsElement(ptav, remainingSpace, PTAVWidth);
                break;
            }
        }
    }

    /**
     * Schedules and batches updates for all active `ProductVariantPreview` instances
     * to refresh their variant previews efficiently.
     * Uses `requestAnimationFrame` to ensure that updates occur in sync with the browser’s
     * rendering cycle, preventing redundant or frequent recalculations (trigger by offsetWidth).
     */
    updateVariantPreview() {
        ProductVariantPreview.instances.push(this);
        if (ProductVariantPreview.currentFrame) {
            return;
        }
        ProductVariantPreview.currentFrame = requestAnimationFrame(() => {
            const instances = ProductVariantPreview.instances.filter(
                (instance) => !instance.isDestroyed
            );
            ProductVariantPreview.currentFrame = null;
            ProductVariantPreview.instances = [];
            if (!instances.length) {
                return;
            }

            for (const instance of instances) {
                instance._resetDisplay();

                const ptav = instance.ptavs[0];
                ptav.classList.remove("d-none");
            }

            for (const instance of instances) {
                const ptav = instance.ptavs[0];
                const containerWidth = instance.el.offsetWidth;
                const PTAVWidth = ptav.offsetWidth;
                instance._updateVariantPreview(containerWidth, PTAVWidth);
            }
        });
    }
}

registry
    .category("public.interactions")
    .add("website_sale.product_variant_preview", ProductVariantPreview);

registry
    .category("public.interactions.edit")
    .add("website.product_variant_preview", { Interaction: ProductVariantPreview });
