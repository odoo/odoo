import { renderToElement } from "@web/core/utils/render";
import options from "@web_editor/js/editor/snippets.options";

options.registry.FloatingBlocks = options.Class.extend({
    /**
     * @override
     */
    start() {
        this.wrapper = this.$target[0].querySelector(".s_floating_blocks_wrapper");

        // The "No cards" message must be injected in the DOM before that the last
        // Card is deleted, otherwise the entire snippet will be removed.
        // The following code will inject the message with "d-none" while the
        // '_validateBoxesNumber' function will eventually toggle its visibility.
        this.noCardsAlert = renderToElement("website_sale.s_floating_blocks.alert.no_cards");
        this.wrapper.appendChild(this.noCardsAlert);
        this._validateBoxesNumber();

        return this._super(...arguments);
    },
    /**
     * @override
     */
    cleanForSave() {
        this.noCardsAlert.remove();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    notify(name) {
        this._super(...arguments);

        if (name === 'card_removed') {
            // Recount Cards number when one is removed.
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
        const newCard = renderToElement("website_sale.s_floating_blocks.new_card");
        this.wrapper.appendChild(newCard);

        newCard.scrollIntoView({behavior: "smooth"});

        // 'scrollIntoView' doesn't have a callback function.
        // Luckily 'setTimeout' it's a decent compromise for our scenario.
        setTimeout(() => {
            // Show the newly injected Card
            newCard.classList.remove("opacity-0");

            // 'oe_unremovable' prevents the unintentional removal of the inner
            // content '<div>' while typing. The class must be added after that
            // the element has been placed into the DOM, otherwise it will not
            // be injected at all.
            newCard.querySelector(".o_block_content").classList.add("oe_unremovable");
        }, 600);

        this._validateBoxesNumber();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _validateBoxesNumber() {
        this.boxes = this.$target[0].querySelectorAll(".o_block");
        this.noCardsAlert.classList.toggle("d-none", this.boxes.length > 0);
    },
});

options.registry.FloatingBlocksBlock = options.Class.extend({
    /**
     * @override
     */
    onRemove () {
        this.trigger_up('option_update', {optionName: 'FloatingBlocks', name: 'card_removed'});
    },
    /**
     * @override
     */
    cleanForSave() {
        this.$target[0].style.transform = "";
        this.$target[0].classList.remove("opacity-0", "transition-base");
    },
});

export default {
    FloatingBlocks: options.registry.FloatingBlocks,
    FloatingBlocksBlock: options.registry.FloatingBlocksBlock,
};
