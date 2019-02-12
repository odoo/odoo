odoo.define('website_slides.progress.bar', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');

    var ProgressBar = publicWidget.Widget.extend({

        /**
         * @override
         * @param {Object} el
         * @param {number} channel_id
         */
        init: function (el, completion) {
            this._super(el);
            this.completion = completion;
        },
        /**
         * @override
         */
        start: function () {
            this._renderProgressBar();
            return this._super.apply(this, arguments);
        },
        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
        _renderProgressBar: function (ev) {
            var self = this;
            $('.oe_slide_js_progress_bar').css('width', (self.completion <= 100 ? self.completion : 100)  + '%');
        },
    });

    publicWidget.registry.websiteSlidesProgressBar = publicWidget.Widget.extend({
        selector: '.oe_slide_js_progress_bar',
        /**
         * @override
         */
        start: function () {
            var completion = parseInt($('.oe_slide_js_progress_bar').attr('channel_completion'));
            var progressBar = new ProgressBar(this, completion);
            progressBar.appendTo(".oe_slide_js_progress_bar");
            return this._super.apply(this, arguments);
        },
    });

    return ProgressBar;
});
