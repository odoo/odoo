odoo.define('website_slides.slides', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var time = require('web.time');

publicWidget.registry.websiteSlides = publicWidget.Widget.extend({
    selector: '#wrapwrap',

    /**
     * @override
     * @param {Object} parent
     */
    start: function (parent) {
        var defs = [this._super.apply(this, arguments)];

        _.each($("timeago.timeago"), function (el) {
            var datetime = $(el).attr('datetime');
            var datetimeObj = time.str_to_datetime(datetime);
            // if presentation 7 days, 24 hours, 60 min, 60 second, 1000 millis old(one week)
            // then return fix formate string else timeago
            var displayStr = '';
            if (datetimeObj && new Date().getTime() - datetimeObj.getTime() > 7 * 24 * 60 * 60 * 1000) {
                displayStr = moment(datetimeObj).format('ll');
            } else {
                displayStr = moment(datetimeObj).fromNow();
            }
            $(el).text(displayStr);
        });

        return Promise.all(defs);
    },
});

return publicWidget.registry.websiteSlides;

});

//==============================================================================

odoo.define('website_slides.slides_embed', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
require('website_slides.slides');

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
        var input = $(ev.currentTarget);
        var page = parseInt(input.val());
        if (!page || page < 1 || this.max_page && page > this.max_page) {
            page = 1;
        }
        input.val(page);
        this._updateEmbeddedCode(page);
    },
});

publicWidget.registry.websiteSlidesEmbed = publicWidget.Widget.extend({
    selector: '.oe_slide_js_embed_code_widget',

    /**
     * @override
     * @param {Object} parent
     */
    start: function (parent) {
        var defs = [this._super.apply(this, arguments)];
        this._timeout = setTimeout(this._checkIframeLoaded.bind(this), 100);
        return Promise.all(defs);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _checkIframeLoaded: function () {
        var $iframe = $('iframe.o_wslides_iframe_viewer');
        var iframeDoc = $iframe[0].contentDocument || $iframe[0].contentWindow.document;
        
        if (iframeDoc.readyState  == 'complete') {
            clearTimeout(this._timeout);
            this._onIframeViewerReady($iframe);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} $iframe
     */
    _onIframeViewerReady: function ($iframe) {
        var maxPage = parseInt($iframe.contents().find('#page_count').text());
        new SlideSocialEmbed(this, maxPage).attachTo($('.oe_slide_js_embed_code_widget'));
    },
});

});
