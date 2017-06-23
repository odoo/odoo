odoo.define('web.rainbow_man', function (require) {
"use strict";

var ajax = require("web.ajax");
var Widget = require('web.Widget');
var core = require('web.core');
var qweb = core.qweb;
var _t = core._t;

ajax.loadXML("/web/static/src/xml/rainbow_man.xml", qweb);

var RainbowMan = Widget.extend({
    template: 'rainbow_man.notification',
    /**
     * @constructor
     * @param {Object} [options] - key-value options to decide rainbowman behavior / appearance
     * @param {string} [options.message] - Message to be displayed on rainbowman card
     * @param {string} [options.fadeout]
     *        Delay for rainbowman to disappear - [options.fadeout='fast'] will make rainbowman
     *        dissapear quickly, [options.fadeout='medium'] and [options.fadeout='slow'] will
     *        wait little longer before disappearing (can be used when [options.message]
     *        is longer), [options.fadeout='no'] will keep rainbowman on screen until
     *        user clicks anywhere outside rainbowman
     * @param {string} [options.img_url] - URL of the image to be displayed
     * @param {Boolean} [options.click_close] - If true, destroys rainbowman on click outside
     */
    init: function (options) {
        var rainbowDelay = {slow: 4500, medium: 3500, fast:2000, no: false };
        this.options = _.defaults(options || {}, {
            fadeout: 'medium',
            img_url: '/web/static/src/img/smile.svg',
            message: _t('Well Done!'),
            click_close: true,
        });
        this.delay = rainbowDelay[this.options.fadeout];
        this._super.apply(this, arguments);
    },
    start: function () {
        var self = this;
        if (this.options.click_close) {
            core.bus.on('click', this, function (ev) {
                if (ev.originalEvent && ev.target.className.indexOf('o_reward') === -1) {
                    this.destroy();
                }
            });
        }
        if (this.delay) {
            setTimeout(function () {
                self.$el.addClass('o_reward_fading');
                setTimeout(function () {
                    self.destroy();
                }, 600); // destroy only after fadeout animation is completed
            }, this.delay);
        }
        this.$('.o_reward_msg_content').append(this.options.message);
        return this._super.apply(this, arguments);
    }
});

return RainbowMan;

});
