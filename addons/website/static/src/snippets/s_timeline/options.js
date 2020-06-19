odoo.define('website.s_timeline_options', function (require) {
'use strict';

const options = require('web_editor.snippets.options');

options.registry.Timeline = options.Class.extend({
    /**
     * @override
     */
    start: function () {
        var $buttons = this.$el.find('we-button');
        var $overlayArea = this.$overlay.find('.o_overlay_options_wrap');
        $overlayArea.append($('<div/>').append($buttons));

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
});
