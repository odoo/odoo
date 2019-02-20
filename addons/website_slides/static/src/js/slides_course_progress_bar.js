odoo.define('website_slides.progress.bar', function (require) {

var sAnimations = require('website.content.snippets.animation');
var Widget = require('web.Widget');

/**
 * TODO awa/qmo:
 * Right now widgets using this progress bar update the progression using
 * a global css selector (= dirty).
 *
 * They should instead instantiate this widget and attach it to the right element of their template
 * structure and then update the progression using methods inside this widget.
 */
var ProgressBar = Widget.extend({

    /**
     * @override
     * @param {integer} options.completion initial progress bar completion (%age)
     */
    init: function (parent, options) {
        this.completion = options.completion;

        this._super(parent, options);
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
        if (this.completion) {
            this.$el.css('width', Math.min(this.completion, 100)  + '%');
        }
    },
});

sAnimations.registry.websiteSlidesProgressBar = sAnimations.Class.extend({
    selector: '.oe_slide_js_progress_bar',

    /**
     * @override
     */
    start: function () {
        var completion = parseInt($('.oe_slide_js_progress_bar').attr('channel_completion'));
        var progressBar = new ProgressBar(this, {completion: completion});
        progressBar.attachTo(".oe_slide_js_progress_bar");

        return this._super.apply(this, arguments);
    },
});

return ProgressBar;

});
