/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import time from '@web/legacy/js/core/time';
const { DateTime } = luxon;

publicWidget.registry.websiteSlides = publicWidget.Widget.extend({
    selector: '#wrapwrap',

    /**
     * @override
     * @param {Object} parent
     */
    start: function (parent) {
        var defs = [this._super.apply(this, arguments)];

        $("timeago.timeago").toArray().forEach((el) => {
            var datetime = $(el).attr('datetime');
            var datetimeObj = time.str_to_datetime(datetime);
            // if presentation 7 days, 24 hours, 60 min, 60 second, 1000 millis old(one week)
            // then return fix formate string else timeago
            var displayStr = '';
            if (datetimeObj && new Date().getTime() - datetimeObj.getTime() > 7 * 24 * 60 * 60 * 1000) {
                displayStr = DateTime.fromJSDate(datetimeObj).toFormat('DD');
            } else {
                displayStr = DateTime.fromJSDate(datetimeObj).toRelative();
            }
            $(el).text(displayStr);
        });

        return Promise.all(defs);
    },
});

export default publicWidget.registry.websiteSlides;

//==============================================================================

var SlideSocialEmbed = publicWidget.Widget.extend({
    events: {
        'change input': '_onChangePage',
    },
    /**
     * @constructor
     * @param {Object} parent
     * @param {Number} maxPage
     */
    init: function (parent, maxPage) {
        this._super.apply(this, arguments);
        this.max_page = maxPage || false;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Number} page
     */
    _updateEmbeddedCode: function (page) {
        var $embedInput = this.$('.slide_embed_code');
        var newCode = $embedInput.val().replace(/(page=).*?([^\d]+)/, '$1' + page + '$2');
        $embedInput.val(newCode);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} ev
     */
    _onChangePage: function (ev) {
        ev.preventDefault();
        var input = this.$('input');
        var page = parseInt(input.val());
        if (this.max_page && !(page > 0 && page <= this.max_page)) {
            page = 1;
        }
        this._updateEmbeddedCode(page);
    },
});

publicWidget.registry.websiteSlidesEmbed = publicWidget.Widget.extend({
    selector: '#wrapwrap',

    /**
     * @override
     * @param {Object} parent
     */
    start: function (parent) {
        var defs = [this._super.apply(this, arguments)];
        $('iframe.o_wslides_iframe_viewer').on('ready', this._onIframeViewerReady.bind(this));
        return Promise.all(defs);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onIframeViewerReady: function (ev) {
        // TODO : make it work. For now, once the iframe is loaded, the value of #page_count is
        // still now set (the pdf is still loading)
        var $iframe = $(ev.currentTarget);
        var maxPage = $iframe.contents().find('#page_count').val();
        new SlideSocialEmbed(this, maxPage).attachTo($('.oe_slide_js_embed_code_widget'));
    },
});
