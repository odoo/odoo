odoo.define('mail.systray.MessagingMenuMobile', function (require) {
"use strict";

var MessagingMenu = require('mail.systray.MessagingMenu');

var config = require('web.config');
var core = require('web.core');
var QWeb = core.qweb;

if (!config.device.isMobile) {
    return;
}

/**
 * Overrides systray messaging module in mobile
 */
MessagingMenu.include({
    jsLibs: [],
    events: _.extend(MessagingMenu.prototype.events, {
        'touchstart .o_mail_preview.o_preview_unread': '_ontouchstart',
        'touchmove .o_mail_preview.o_preview_unread': '_onSwipPreview',
        'touchend .o_mail_preview.o_preview_unread': '_ontouchend',
    }),

    init: function () {
        this._super.apply(this, arguments);
        this.jsLibs.push('/web/static/lib/jquery.touchSwipe/jquery.touchSwipe.js');
    },
    /**
     * @private
     * When a preview touch start
     */
    _ontouchstart: function (ev) {
        $(ev.currentTarget).prepend($(QWeb.render('mail.mobile.swip', {bgColor:'grey', icon:'fa-check fa-2x'})));
    },
    /**
     * @private
     * When a preview touch end
     */
    _ontouchend: function (ev) {
        $(ev.currentTarget).find("div[class~='o_thread_swip']").remove();
    },
     /**
     * When a preview is swip on, we want to read the related object
     * (thread, mail failure, etc.)
     *
     * @private
     * @param {Touch} ev
     */
    _onSwipPreview: function (ev) {
        ev.stopPropagation();
        var $target = $(ev.currentTarget);
        $(ev.currentTarget).swipe({
            swipeStatus:function(event, phase, direction, distance, duration, fingers, fingerData, currentDirection) {
                if (direction == 'right') {
                    $target.find('> div:first-child').css({"min-width": distance + "px"});
                    var swipeDistance = (distance / $(window).width()) * 100;
                    if (swipeDistance > 20) {
                        $target.find('> div:first-child').css({"background-color": "green"});
                        if (swipeDistance > 30) {
                            $target.find("span[class~='o_mail_preview_mark_as_read']").click();
                        }
                    }
                }
            }
        });
    },
});
});
