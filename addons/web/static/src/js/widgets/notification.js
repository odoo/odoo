odoo.define('web.Notification', function (require) {
"use strict";

/**
 * Notification
 *
 * This file contains the widget which is used to display a warning/information
 * message in the top right of the screen.
 *
 * If you want to display such a notification, you probably do not want to do it
 * by importing this file. The proper way is to use the do_warn or do_notify
 * methods on the Widget class.
 */

var Widget = require('web.Widget');

var Notification = Widget.extend({
    template: 'Notification',
    events: {
        'click .o_close': '_onClose',
    },
    /**
     * @override
     * @param {Widget} parent
     * @param {Object} params
     * @param {string} params.title notification title
     * @param {string} params.text notification main text
     * @param {string} params.type 'notification' or 'warning'
     * @param {boolean} [params.sticky=false] if true, the notification will stay
     *   visible until the user clicks on it.
     */
    init: function (parent, params) {
        this._super.apply(this, arguments);
        this.title = params.title;
        this.text = params.text;
        this.sticky = !!params.sticky;
        if (params.type === 'warning') {
            this.template = 'Warning';
        }
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.$el.animate({opacity: 1.0}, 400, "swing", function () {
                if(!self.sticky) {
                    setTimeout(self._destroy.bind(self), 2500);
                }
            });
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * This method is used to destroy the widget with a nice animation.  We
     * first perform an animation, then call the real destroy method.
     *
     * @private
     */
    _destroy: function () {
        var self = this;
        this.$el.animate({opacity: 0.0}, 400, "swing", function() {
            self.$el.animate({height: 0}, 400, "swing", self.destroy.bind(self));
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClose: function (ev) {
        ev.preventDefault();
        this._destroy();
    },
});

return Notification;

});
