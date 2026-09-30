import { convertNumericToUnit, getHtmlStyle } from "@html_editor/utils/formatting";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class FloatingBlocks extends Interaction {
    static selector = ".s_floating_blocks";

    dynamicContent = {
        _window: {
            "t-on-resize": this.debounced(this.onResize, 100),
            "t-on-scroll": this.throttled(this.onScroll),
        },
        ".s_floating_blocks_block": {
            "t-att-style": (blockEl) => ({
                opacity: "1",
                top: this.boxesTops.get(blockEl),
                transform: this.boxesTransforms.get(blockEl),
            }),
            "t-on-keydown": this.onKeydown,
        },
    };

    setup() {
        this.boxScaleStep = 0.02;
        this.maximalScale = 0.98;
        this.minimalScale = this.maximalScale;

        this.boxesEls = this.el.querySelectorAll(".s_floating_blocks_block");

        this.initialGap = 16; // Provide a visual gap by default
        this.stackingGap = this.initialGap * 0.8;

        this.boxesTops = new WeakMap();
        this.boxesTransforms = new WeakMap();
        this.boxesToAnimate = [];
        this.boxesScaleStep = [];
        this.boxesScaleProp = [];
    }

    start() {
        this.adaptToHeaderChange();
        this.registerCleanup(
            this.services.website_menus.registerCallback(this.adaptToHeaderChange.bind(this))
        );

        if (this.boxesEls.length >= 2) {
            // The last block does not need to be animated
            this.boxesToAnimate = Array.from(this.boxesEls).slice(0, -1);

            // Calculate the minimal scale based on number of animated cards.
            // Each card decreases the scale by `this.boxScaleStep`.
            this.minimalScale = Math.max(
                this.maximalScale - this.boxScaleStep * (this.boxesToAnimate.length - 1),
                0.7 // Safe-net to ensure we don't go below 0.7 for very large numbers of cards
            );

            // Calculate scale factors for each card
            this.boxesScaleStep = this.calculateScaleFactors();

            this.onResize();
            this.onScroll();
            this.updateContent();
        }
    }

    /**
     * Calculates proportional scale factors for each card and pre-compute
     * transforms.
     *
     * @returns {Array<number>} Array of scale factors
     */
    calculateScaleFactors() {
        const boxesLength = this.boxesToAnimate.length;
        const boxesScaleStep = [];
        if (boxesLength === 0) {
            return boxesScaleStep;
        }

        // If only one card to animate, use this.maximalScale
        if (boxesLength === 1) {
            boxesScaleStep.push(this.maximalScale);
            this.boxesScaleProp[0] = `scale3d(${this.maximalScale}, ${this.maximalScale}, ${this.maximalScale})`;

            return boxesScaleStep;
        }

        // Calculate the step between each card's scale
        const scaleStep = (this.maximalScale - this.minimalScale) / (boxesLength - 1);

        // Assign proportional scale factors and pre-compute transforms
        for (let i = 0; i < boxesLength; i++) {
            const scale = this.minimalScale + scaleStep * i;
            boxesScaleStep.push(scale);

            // Pre-compute the transform string for this scale
            this.boxesScaleProp[i] = `scale3d(${scale}, ${scale}, ${scale})`;
        }

        return boxesScaleStep;
    }

    /**
     * Updates stacking offset of each box.
     */
    adaptToHeaderChange() {
        let top = this.initialGap;
        for (const el of this.el.ownerDocument.querySelectorAll(".o_top_fixed_element")) {
            top += el.offsetHeight;
        }
        this.boxesEls.forEach((boxEl, index) => {
            this.boxesTops.set(boxEl, `${top + this.stackingGap * index}px`);
        });
    }

    /**
     * Adapts the zoom animation values.
     */
    updateZoom() {
        const scrollTop = window.scrollY;
        this.boxesToAnimate.forEach((blockEl, i) => {
            const blockGap = scrollTop - this.snippetOffset - this.snippetHeight * i;
            const transformValue = this.computeTransform(blockGap, i);
            this.boxesTransforms.set(blockEl, transformValue);
        });
    }

    /**
     * Computes a block transform based on given environment values.
     *
     * @param {number} blockGap - Gap between the block and its target position
     * @param {number} index - Index of the block in boxesToAnimate array
     * @returns {string} CSS transform value
     */
    computeTransform(blockGap, index) {
        // If block is at or above initial position, use the initial transform
        if (blockGap <= 0) {
            return "scale3d(1, 1, 1)";
        }

        const targetScale = this.boxesScaleStep[index];
        const scale = Math.max(targetScale, 1 - blockGap * this.snippetScaleFactor);

        // Return pre-computed value if it's close enough to the target scale
        if (Math.abs(scale - targetScale) < 0.001) {
            return this.boxesScaleProp[index];
        }

        // Calculate and return the transform for intermediate values
        return `scale3d(${scale}, ${scale}, ${scale})`;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * On page resize, updates the animation.
     */
    onResize() {
        this.viewportHeight = window.innerHeight;
        this.snippetHeight = Math.min(
            this.boxesEls[0]?.offsetHeight || 0,
            window.innerHeight - 100
        );
        this.snippetOffset = this.el.getBoundingClientRect().y + window.scrollY;
        this.snippetScaleFactor = 1 / (this.snippetHeight * 12);

        this.updateZoom();
    }

    /**
     * On page scroll, updates the animation.
     */
    onScroll() {
        this.updateZoom();
    }
    /**
     * Support Shift+Tab navigation
     *
     * @param {KeyboardEvent} ev
     */
    onKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === "shift+tab") {
            this.addListener(ev.currentTarget, "focusout", this.onShiftTabFocusout.bind(this), {
                once: true,
            });
        }
    }
    onShiftTabFocusout(ev) {
        if (
            !ev.relatedTarget ||
            ev.relatedTarget.closest(".s_floating_blocks_block") === ev.currentTarget
        ) {
            return;
        }
        // Account for `.gap-5` on the container.
        const gap = convertNumericToUnit(3, "rem", "px", getHtmlStyle(document));
        scrollTo(0, window.scrollY - (this.snippetHeight + gap));
    }
}

registry.category("public.interactions").add("website.floating_blocks", FloatingBlocks);
