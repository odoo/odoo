import { renderToElement } from "@web/core/utils/render";
import weUtils from "@web_editor/js/common/utils";
import options from "@web_editor/js/editor/snippets.options";

options.registry.FloatingBlocks = options.Class.extend({
    /**
     * @override
     */
    start() {
        this.wrapperEl = this.$target[0].querySelector(".s_floating_blocks_wrapper");
        this.alertEl = this.wrapperEl.querySelector(".s_floating_blocks_alert_empty");
        this.boxes = this.wrapperEl.querySelectorAll(".o_block");

        this._validateBoxesNumber();
        return this._super(...arguments);
    },
    /**
     * @override
     */
    cleanUI() {
        (this.boxes.length > 0 ? this.alertEl : this.$target[0])?.remove();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    notify(action) {
        this._super(...arguments);

        if (action === 'card_removed') {
            // Recount Cards number when one is removed.
            // See 'options.registry.FloatingBlocksBlock' -> 'onRemove()'
            this.trigger_up('snippet_edition_request', {exec: () => {
                return this._validateBoxesNumber();
            }});
        }
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Injects a new Card.
     */
    addCard() {
        const newCard = renderToElement("website.s_floating_blocks.new_card");
        this.wrapperEl.appendChild(newCard);

        newCard.scrollIntoView({behavior: "smooth", block: "center"});

        // Wait for the card to scroll into view, then fade it in.
        // 'scrollIntoView' doesn't have a callback function, luckily
        // 'setTimeout' it's a decent compromise in our scenario.
        setTimeout(() => {
            newCard.classList.remove("opacity-0");
        }, 600);

        this._validateBoxesNumber();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Validates the number of Cards.
     * Toggles the visibility of the "No cards" alert based on the card count.
     * Ensures the alert is present but hidden until there are no cards left.
     *
     * @private
     */
    async _validateBoxesNumber() {
        const boxesNew = this.wrapperEl.querySelectorAll(".o_block");

        if (this.boxes != boxesNew) {
            this.boxes = boxesNew;
            // Refresh public widgets
            await this._refreshPublicWidgets();
        }

        this._injectAlert();
        this.alertEl.classList.toggle("css_non_editable_mode_hidden", this.boxes.length === 0);
    },
    /**
     * Injects the "No cards" alert into the DOM.
     *
     * The message must be injected regardless by the actual cards number and
     * anyway *before* the removal of the last Card, otherwise the resulting
     * empty snippet could be automatically removed by the editor.
     *
     * @private
     */
    _injectAlert() {
        if (!this.alertEl) {
            this.alertEl = renderToElement("website.s_floating_blocks.alert.empty");
            this.wrapperEl.appendChild(this.alertEl);
        }
    },
});

options.registry.FloatingBlocksBlock = options.Class.extend({
    /**
     * @override
     */
    onRemove() {
        this.trigger_up('option_update', {optionName: 'FloatingBlocks', name: 'card_removed'});
    },
    /**
     * @override
     */
    cleanUI() {
        this.$target[0].style.transform = "";
        this.$target[0].classList.remove("opacity-0", "transition-base");
    },
});

options.registry.FloatingBlocksBlockGrid = options.Class.extend({
    /**
     * @override
     */
    _computeWidgetVisibility(widgetName, params) {
        // Show the vertical alignment widget on mobile only
        if (widgetName === "block_alignment_mobile_opt") {
            return weUtils.isMobileView(this.$target[0]);
        }
        return this._super(...arguments);
    },
});

export default {
    FloatingBlocks: options.registry.FloatingBlocks,
    FloatingBlocksBlock: options.registry.FloatingBlocksBlock,
    FloatingBlocksBlockGrid: options.registry.FloatingBlocksBlockGrid
};
