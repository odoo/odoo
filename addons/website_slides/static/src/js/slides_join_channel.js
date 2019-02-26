odoo.define('website_slides.slides_join_channel', function (require) {
'use strict';

var core = require('web.core');
var Widget = require('web.Widget');
var sAnimations = require('website.content.snippets.animation');
require('website_slides.slides');

var _t = core._t;

var JoinChannelButton = Widget.extend({
    events: {
        'click .o_wslides_join_channel_link': '_onClickJoin',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} $el
     * @param {String} message
     */
    _popoverAlert: function ($el, message) {
        $el.popover({
            trigger: 'focus',
            placement: 'bottom',
            container: 'body',
            html: true,
            content: function () {
                return message;
            }
        }).popover('show');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickJoin: function (event) {
        var channelId = $(event.currentTarget).data('channel-id');
        var self = this;
        this._rpc({
            route: '/slides/channel/join',
            params: {
                channel_id: channelId,
            },
        }).then(function (data) {
            if (! data.error) {
                location.reload();
            } else {
                if (data.error === 'public_user') {
                    self._popoverAlert(self.$el, _.str.sprintf(_t('Please <a href="/web/login?redirect=%s">login</a> to join this course.'), (document.URL)));
                } else if (data.error === 'join_done') {
                    self._popoverAlert(self.$el, _t('You have already joined this channel'));
                } else {
                    self._popoverAlert(self.$el, _t('Unknown error'));
                }
            }
        });
    },
});

sAnimations.registry.websiteSlidesJoinChannel = sAnimations.Class.extend({
    selector: '#wrapwrap',

    /**
     * @override
     * @param {Object} parent
     */
    start: function () {
        var defs = [this._super.apply(this, arguments)];
        defs.push(new JoinChannelButton(this).attachTo($('.o_wslides_join_channel')));
        return $.when.apply($, defs);
    },
});
});
