import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class FloatingBlocks extends Interaction {
    static selector = ".s_floating_blocks";

    setup() {
        this.zoomMax = 0.86;
        this.boxes = this.el.querySelectorAll(".o_block");
        this.boxesToAnimate = [];
        this.transformCache = new WeakMap();
        this.onScrollThrottled = this.throttled(this._onScroll);
    }

    start() {
        this._cleanUp();

        this._adaptToHeaderChange();
        this.registerCleanup(this.services.website_menus.registerCallback(this._adaptToHeaderChange.bind(this)));

        this.addListener(window, "resize", this._onResize.bind(this));
        this.addListener(window, "scroll", this.onScrollThrottled);

        if (this.boxes.length >= 2) {
            this._initiateZoomAnimation();
        }
    }

    destroy() {
        this._cleanUp();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _initiateZoomAnimation() {
        // The last block does not need to be animated
        this.boxesToAnimate = Array.from(this.boxes).slice(0, -1);

        // Initial trigger
        this._onResize();
        this._onScroll();
    }

    /**
     * @private
     */
    _adaptToHeaderChange() {
        let position = 16; // Add 1rem equivalent in px to provide a visual gap by default
        const fixedElements = this.el.ownerDocument.querySelectorAll(".o_top_fixed_element");

        Array.from(fixedElements).forEach((el) => position += el.offsetHeight);

        Array.from(this.boxes).forEach((box) => {
            box.style.top = `${position}px`;
        });
    }

    /**
     * @private
     */
    _zoomAnimation() {
        const scrollTop = window.scrollY;
        const animationsBatch = []; // Batch DOM style changes

        this.boxesToAnimate.forEach((block, i) => {
            const blockGap = scrollTop - this.snippetOffset - this.snippetHeight * i;
            const transformValue = this._computeTransform(blockGap, i, this.snippetHeight);

            // Push into batch if the transform value has changed only
            if (this.transformCache.get(block) !== transformValue) {
                this.transformCache.set(block, transformValue);
                animationsBatch.push(() => (block.style.transform = transformValue));
            }
        });

        // Apply all batch changes at once
        if (animationsBatch.length > 0) {
            this.waitForAnimationFrame(() => animationsBatch.forEach((animation) => animation()));
        }
    }

    /**
     * @private
     * @param {number} blockGap - Gap between the block and its target position
     * @returns {string} CSS transform value
     */
    _computeTransform(blockGap) {
        if (blockGap > 0) {
            const scale = Math.max(this.zoomMax, 1 - blockGap * this.snippetScaleFactor);
            return `scale3d(${scale}, ${scale}, ${scale})`;
        }
        return "scale3d(1, 1, 1)";
    }

    /**
     * @private
     */
    _cleanUp() {
        if (this.boxes.length > 0) {
            this.boxes.forEach((box) => {
                box.style.transform = "";
                box.style.top = "";
            });
        }
    }

    /**
     * Checks if the element is currently visible in the viewport
     * @private
     */
    _isInViewport() {
        if (!this.el.isConnected) return false;

        const elRect = this.el.getBoundingClientRect();
        this.isVisible = ( elRect.top < this.viewportHeight + 100 && elRect.bottom > -100 );

        return this.isVisible;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onResize() {
        this.viewportHeight = window.innerHeight;
        this.snippetHeight = Math.min(
            this.boxes[0].offsetHeight,
            window.innerHeight - 100
        );
        this.snippetOffset = this.el.getBoundingClientRect().y + window.scrollY;
        this.snippetScaleFactor = 1 / (this.snippetHeight * 12);
    }

    /**
     * @private
     */
    _onScroll() {
        if (this._isInViewport()) {
            this._zoomAnimation();
        }
    }
}

registry
    .category("public.interactions")
    .add("website.floating_blocks", FloatingBlocks);
