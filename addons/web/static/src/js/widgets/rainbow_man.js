odoo.define('web.RainbowMan', function (require) {
"use strict";

/**
 * The RainbowMan widget is the widget displayed by default as a 'fun/rewarding'
 * effect in some cases.  For example, when the user marked a large deal as won,
 * or when he cleared its inbox.
 *
 * This widget is mostly a picture and a message with a rainbow animation around
 * If you want to display a RainbowMan, you probably do not want to do it by
 * importing this file.  The usual way to do that would be to use the effect
 * service (by triggering the 'show_effect' event)
 */

var Widget = require('web.Widget');
var core = require('web.core');

var _t = core._t;

var RainbowMan = Widget.extend({
    template: 'rainbow_man.notification',
    xmlDependencies: ['/web/static/src/xml/rainbow_man.xml'],
    /**
     * @override
     * @constructor
     * @param {Object} [options]
     * @param {string} [options.message] Message to be displayed on rainbowman card
     * @param {string} [options.fadeout='medium'] Delay for rainbowman to disappear
     *   [options.fadeout='fast'] will make rainbowman dissapear quickly,
     *   [options.fadeout='medium'] and [options.fadeout='slow'] will wait
     *     little longer before disappearing (can be used when [options.message]
     *     is longer),
     *   [options.fadeout='no'] will keep rainbowman on screen until user clicks
     *     anywhere outside rainbowman
     * @param {string} [options.img_url] URL of the image to be displayed
     * @param {boolean} [options.click_close=true] If true, destroys rainbowman on
     *   click outside
     */
    init: function (options) {
        this._super.apply(this, arguments);
        var rainbowDelay = {slow: 4500, medium: 3500, fast:2000, no: false };
        this.options = _.defaults(options || {}, {
            fadeout: 'medium',
            img_url: '/web/static/src/img/smile.svg',
            message: _t('Well Done!'),
            click_close: true,
        });
        this.delay = rainbowDelay[this.options.fadeout];
        core.bus.on('clear_uncommitted_changes', this, this.destroy);
    },
    /**
     * @override
     */
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
