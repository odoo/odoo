odoo.define('website_event_track.website_event_track_reminder', function (require) {
'use strict';

var core = require('web.core');
var _t = core._t;
var utils = require('web.utils');
var publicWidget = require('web.public.widget');

publicWidget.registry.websiteEventTrackReminder = publicWidget.Widget.extend({
    selector: '.o_wetrack_js_reminder',
    events: {
        'click': '_onReminderToggleClick',
    },

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this._onReminderToggleClick = _.debounce(this._onReminderToggleClick, 500, true);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //-------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onReminderToggleClick: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        var self = this;
        var $trackLink = $(ev.currentTarget).find('i');

        if (this.reminderOn === undefined) {
            this.reminderOn = $trackLink.data('reminderOn');
        }

        this._rpc({
            route: '/event/track/toggle_reminder',
            params: {
                track_id: $trackLink.data('trackId'),
                set_reminder_on: !this.reminderOn
            },
        }).then(function (result) {
            if (result.error && result.error === 'ignored') {
                self.displayNotification({
                    type: 'info',
                    title: _t('Error'),
                    message: _.str.sprintf(_t('Unknown issue, please retry')),
                });
            } else {
                self.reminderOn = result.reminderOn;
                var reminderText = self.reminderOn ? _t('Reminder On') : _t('Set a Reminder');
                self.$('.o_wetrack_js_reminder_text').text(reminderText);
                self._updateDisplay();
                var message = self.reminderOn ? _t('Talk added to your wishlist') : _t('Talk removed from your wishlist');
                self.displayNotification({
                    type: 'info',
                    title: message
                });
            }
            if (result.visitor_uuid) {
                utils.set_cookie('visitor_uuid', result.visitor_uuid);
            }
        });
    },

    _updateDisplay: function () {
        var $trackLink = this.$el.find('i');
        if (this.reminderOn) {
            $trackLink.addClass('fa-bell').removeClass('fa-bell-o');
            $trackLink.attr('title', _t('Reminder On'));
        } else {
            $trackLink.addClass('fa-bell-o').removeClass('fa-bell');
            $trackLink.attr('title', _t('Set a reminder'));
        }
    },

});

return publicWidget.registry.websiteEventTrackReminder;

});
