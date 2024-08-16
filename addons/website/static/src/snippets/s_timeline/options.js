/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";

options.registry.Timeline = options.Class.extend({
    displayOverlayOptions: true,

    /**
     * @override
     */
    start: function () {
        var $buttons = this.$el.find('we-button.o_we_overlay_opt');
        var $overlayArea = this.$overlay.find('.o_overlay_options_wrap');
        $overlayArea.append($buttons);

        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Moves the card to the right/left.
     *
     * @see this.selectClass for parameters
     */
    timelineCard(previewMode, widgetValue, params) {
        const timelineRowEl = this.$target[0].closest(".s_timeline_row");
        timelineRowEl.classList.toggle("flex-md-row-reverse");
        timelineRowEl.classList.toggle("flex-md-row");
        this.$target[0].classList.toggle("text-md-end");
    },
});
