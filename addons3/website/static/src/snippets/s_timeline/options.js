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
    timelineCard: function (previewMode, widgetValue, params) {
        const $timelineRow = this.$target.closest('.s_timeline_row');
        $timelineRow.toggleClass('flex-row-reverse flex-row');
    },
});
