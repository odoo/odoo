/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

/**
 * Simple widget that shows a small popup to request the notifications permission.
 * We use a jQuery 'dropdown' menu so that it automatically closes when clicked outside.
 */
const NotificationRequestPopup = publicWidget.Widget.extend({
    template: 'social_push_notifications.NotificationRequestPopup',
    events: {
        'click .o_social_push_notifications_permission_allow': '_onClickAllow',
        'click .o_social_push_notifications_permission_deny': '_onClickDeny'
    },

    init: function (parent, options) {
        this._super.apply(this, arguments);

        this.notificationTitle = options.title;
        this.notificationBody = options.body;
        this.notificationDelay = options.delay;
        this.notificationIcon = options.icon;
    },

    /**
     * Will start the timer to display the notification request popup.
     *
     * Also pushes down the notification window if the main menu nav bar is active.
     * (We want to avoid covering the nav bar with the notification window)
     *
     * @override
     */
    start: function () {
        var self = this;

        return this._super.apply().then(function () {
            var $mainNavBar = $('#oe_main_menu_navbar');
            if ($mainNavBar && $mainNavBar.length !== 0){
                self.$el.addClass('o_social_push_notifications_permission_with_menubar');
            }
            self.timer = setTimeout(self._toggleDropdown.bind(self), self.notificationDelay * 1000);
            const dropdown = self.$el.find('.dropdown');
            dropdown.on('hide.bs.dropdown', () => {
                self.destroy();
            });
        });
    },

    /**
     * @override
     */
    destroy: function () {
        this._super(...arguments);
        if (this.timer) {
            clearTimeout(this.timer);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickAllow: function () {
        this.trigger_up('allow');
    },

    _onClickDeny: function () {
        this.trigger_up('deny');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Will display the notification window by toggling the popup.
     *
     * @private
     */
    _toggleDropdown: function () {
        this.$('.dropdown-toggle').dropdown('toggle');
    }
});

export default NotificationRequestPopup;
