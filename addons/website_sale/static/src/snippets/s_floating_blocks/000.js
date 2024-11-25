
import {extraMenuUpdateCallbacks} from "@website/js/content/menu";
import {throttleForAnimation} from "@web/core/utils/timing";
import publicWidget from "@web/legacy/js/public/public_widget";

const FloatingBlocks = publicWidget.Widget.extend({
    selector: ".s_floating_blocks",
    disabledInEditableMode: false,

    /**
     * @override
     */
    start() {
        this.zoomMax = 0.86;
        this.boxes = this.el.querySelectorAll(".o_block");

        this._cleanUp();

        if (this.boxes.length < 2) {
            return;
        } else {
            this._initiateZoomAnimation();
        }

        return this._super(...arguments);
    },

    /**
     * @override
     */
    destroy() {
        this._cleanUp();
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _initiateZoomAnimation() {
        // The last block doesn't need to be animated
        this.boxesToAnimate = Array.from(this.boxes).slice(0, -1);

        // Use a WeakMap to store information directly associated with each
        // DOM element.
        this.transformCache = new WeakMap();

        // Adjust boxes position according to the top-menu visibility
        this._adaptToHeaderChange();
        this._adaptToHeaderChangeBound = this._adaptToHeaderChange.bind(this);
        extraMenuUpdateCallbacks.push(this._adaptToHeaderChangeBound);

        this._bindEvents();

        // Initial trigger
        this._onResize();
        this._onScroll();
    },

    /**
     * @private
     */
    _adaptToHeaderChange() {
        let position = 16; // Add 1rem equivalent in px to provide a visual gap by default
        const fixedElements = document.getElementsByClassName('o_top_fixed_element');

        Array.from(fixedElements).forEach((el) => position += el.offsetHeight);

        Array.from(this.boxes).forEach((box) => {
            box.style.top = `${position}px`;
        });
    },

    /**
     * Attach scroll and resize handlers
     *
     * @private
     */
    _bindEvents() {
        this.throttledUpdateResize = throttleForAnimation(() => this._onResize());
        this.throttledUpdateScroll = throttleForAnimation(() => this._onScroll());
        window.addEventListener("resize", this.throttledUpdateResize, { passive: true });
        window.addEventListener("scroll", this.throttledUpdateScroll, { passive: true });
    },

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
            requestAnimationFrame(() => animationsBatch.forEach((animationsBatch) => animationsBatch()));
        }
    },

    /**
     * @private
     */
    _computeTransform(blockGap) {
        if (blockGap > 0) {
            const scale = Math.max(this.zoomMax, 1 - blockGap * this.snippetScaleFactor);
            return `scale3d(${scale}, ${scale}, ${scale})`;
        } else {
            return "scale3d(1, 1, 1)";
        }
    },

    /**
     * @private
     */
    _cleanUp() {
        const indexCallback = extraMenuUpdateCallbacks.indexOf(this._adaptToHeaderChangeBound);
        if (indexCallback >= 0) {
            extraMenuUpdateCallbacks.splice(indexCallback, 1);
        }

        if (this.boxes.length > 0) {
            this.boxes.forEach((box) => {
                box.style.transform = "";
                box.style.top = "";
            });
        }

        window.removeEventListener("scroll", this.throttledUpdateScroll);
        window.removeEventListener("resize", this.throttledUpdateResize);
    },

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
    },

    /**
     * @private
     */
    _onScroll() {
        this._zoomAnimation();
    },
});

publicWidget.registry.FloatingBlocks = FloatingBlocks;

export default FloatingBlocks;
