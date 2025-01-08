import {extraMenuUpdateCallbacks} from "@website/js/content/menu";
import publicWidget from "@web/legacy/js/public/public_widget";

const faqHorizontal = publicWidget.Widget.extend({
    selector: '.s_faq_horizontal',
    disabledInEditableMode: false,

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);

        this.titles = this.$el[0].getElementsByClassName('s_faq_horizontal_entry_title');

        this._updateTitlesPosition();
        this._updateTitlesPositionBound = this._updateTitlesPosition.bind(this);
        extraMenuUpdateCallbacks.push(this._updateTitlesPositionBound);
    },
    /**
     * @override
     */
    destroy() {
        const indexCallback = extraMenuUpdateCallbacks.indexOf(this._updateTitlesPositionBound);
        if (indexCallback >= 0) {
            extraMenuUpdateCallbacks.splice(indexCallback, 1);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _updateTitlesPosition() {
        let position = 16; // Add 1rem equivalent in px to provide a visual gap by default
        const fixedElements = document.getElementsByClassName('o_top_fixed_element');

        Array.from(fixedElements).forEach((el) => position += el.offsetHeight);

        Array.from(this.titles).forEach((title) => {
            title.style.top = `${position}px`;
            title.style.maxHeight = `calc(100vh - ${position + 40}px)`;
        });
    },
});

publicWidget.registry.snippetFaqHorizontal = faqHorizontal;

export default faqHorizontal;
