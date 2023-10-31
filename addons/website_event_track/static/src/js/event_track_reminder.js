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

        var reminderOnValue = !this.reminderOn;

        this._rpc({
            route: '/event/track/toggle_reminder',
            params: {
                track_id: $trackLink.data('trackId'),
                set_reminder_on: reminderOnValue,
            },
        }).then(function (result) {
            if (result.error && result.error === 'ignored') {
                self.displayNotification({
                    type: 'info',
                    title: _t('Error'),
                    message: _.str.sprintf(_t('Talk already in your Favorites')),
                });
            } else {
                self.reminderOn = reminderOnValue;
                var reminderText = self.reminderOn ? _t('Favorite On') : _t('Set Favorite');
                self.$('.o_wetrack_js_reminder_text').text(reminderText);
                self._updateDisplay();
                var message = self.reminderOn ? _t('Talk added to your Favorites') : _t('Talk removed from your Favorites');
                self.displayNotification({
                    type: 'info',
                    title: message
                });
                if (self.reminderOn) {
                    core.bus.trigger('open_notification_request', 'add_track_to_favorite', {
                        title: _t('Allow push notifications?'),
                        body: _t('You have to enable push notifications to get reminders for your favorite tracks.'),
                        delay: 0
                    });
                }
            }
            if (result.visitor_uuid) {
                utils.set_cookie('visitor_uuid', result.visitor_uuid);
            }
        });
    },

    _updateDisplay: function () {
        var $trackLink = this.$el.find('i');
        var isReminderLight = $trackLink.data('isReminderLight');
        if (this.reminderOn) {
            $trackLink.addClass('fa-bell').removeClass('fa-bell-o');
            $trackLink.attr('title', _t('Favorite On'));

            if (!isReminderLight) {
                this.$el.addClass('btn-primary');
                this.$el.removeClass('btn-outline-primary');
            }
        } else {
            $trackLink.addClass('fa-bell-o').removeClass('fa-bell');
            $trackLink.attr('title', _t('Set Favorite'));

            if (!isReminderLight) {
                this.$el.removeClass('btn-primary');
                this.$el.addClass('btn-outline-primary');
            }
        }
    },

});

return publicWidget.registry.websiteEventTrackReminder;

});
