import { renderToElement } from "@web/core/utils/render";
import weUtils from "@web_editor/js/common/utils";
import options from "@web_editor/js/editor/snippets.options";

options.registry.FloatingBlocks = options.Class.extend({
    /**
     * @override
     */
    start() {
        this.wrapperEl = this.$target[0].querySelector(".s_floating_blocks_wrapper");
        this.boxesEls = Array.from(this.wrapperEl.querySelectorAll(".s_floating_blocks_block"));

        // The "No card" message must be injected on start and *before* the
        // removal of the last block, otherwise the snippet could be
        // automatically removed by the editor during edition.
        this.alertEl = renderToElement("website.s_floating_blocks.alert.empty");
        this.wrapperEl.appendChild(this.alertEl);

        this._validateBoxesNumber();
        return this._super(...arguments);
    },

    /**
     * @override
     */
    cleanForSave() {
        if (this.boxesEls.length > 0) {
            this.alertEl.remove();
        } else {
            // Special case: by injecting the "No cards" alert ('alertEl'), we
            // prevent the automatic snippet removal during edition. Still, if
            // the user intentionally "saves" the snippet empty, we'll emulate
            // the original editor behavior by removing it here.
            this.$target[0].remove();
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    notify(action) {
        this._super(...arguments);

        if (action === 'card_cloned' || action === 'card_removed' || action === 'card_moved') {
            // Slightly delay the reinitializations for `card_removed` because
            // the `onRemove` event is fired before that the element is removed
            // from the DOM.

            setTimeout(() => {
                this._validateBoxesNumber();
                this._refreshPublicWidgets(); // FIXME, this should be automatic
            }, 0);
        }
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Injects a new Card.
     */
    addCard() {
        const newCardEl = renderToElement("website.s_floating_blocks.new_card");
        this.wrapperEl.appendChild(newCardEl);
        newCardEl.scrollIntoView({behavior: "smooth", block: "center"});
        this._validateBoxesNumber();

        this.trigger_up("activate_snippet", {
            $snippet: $(newCardEl),
            ifInactiveOptions: true,
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Validates the number of Cards.
     *
     * @private
     */
    _validateBoxesNumber() {
        this.boxesEls = Array.from(this.$target[0].querySelectorAll(".s_floating_blocks_block"));
        this.alertEl.classList.toggle("d-none", this.boxesEls.length > 0);
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
    onClone() {
        this.trigger_up('option_update', {optionName: 'FloatingBlocks', name: 'card_cloned'});
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    updateUI() {
        // FIXME: Currently (saas-18.2), `onMove` is not correctly fired. Handle
        // this scenario manually by using custom events.
        const moveButtonsEls = this.$overlay[0].querySelectorAll("[data-move-snippet]");
        moveButtonsEls.forEach(moveButtonEl => {
            moveButtonEl.addEventListener('click', () => {
                this.trigger_up('option_update', { optionName: 'FloatingBlocks', name: 'card_moved' });
            });
        });
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
