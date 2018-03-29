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
        'click > .o_close': '_onClose',
        'click .o_buttons button': '_onClickButton'
    },
    _autoCloseDelay: 2500,
    _animationDelay: 400,
    /**
     * @override
     * @param {Widget} parent
     * @param {Object} params
     * @param {string} params.title notification title
     * @param {string} params.message notification main message
     * @param {string} params.type 'notification' or 'warning'
     * @param {boolean} [params.sticky=false] if true, the notification will stay
     *   visible until the user clicks on it.
     * @param {string} [params.className] className to add on the dom
     * @param {function} [params.onClose] callback when the user click on the x
     *   or when the notification is auto close (no sticky)
     * @param {Object[]} params.buttons
     * @param {function} params.buttons[0].click callback on click
     * @param {boolean} [params.buttons[0].primary] display the button as primary
     * @param {string} [params.buttons[0].text] button label
     * @param {string} [params.buttons[0].icon] font-awsome className or image src
     */
    init: function (parent, params) {
        this._super.apply(this, arguments);
        this.title = params.title;
        this.message = params.message;
        this.buttons = params.buttons || [];
        this.sticky = !!this.buttons.length || !!params.sticky;
        this.type = params.type || 'notification';
        this.className = params.className || '';
        this._closeCallback = params.onClose;
        this.icon = 'fa-lightbulb-o';
        if (this.buttons && this.buttons.length) {
            this.icon = 'fa-question-circle-o';
        }
        if (this.type === 'warning') {
            this.icon = 'fa-exclamation';
            this.className += ' o_error';
        }
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.$el.animate({opacity: 1.0}, self._animationDelay, "swing", function () {
                if(!self.sticky) {
                    setTimeout(function () {
                        self.close();
                    }, self._autoCloseDelay);
                }
            });
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * This method is used to destroy the widget with a nice animation. We
     * first perform an animation, then call the real destroy method.
     *
     * @private
     * @param {boolean} [silent=false] if true, the notification does not call
     *   _closeCallback method
     */
    close: function (silent) {
        var self = this;
        this.trigger_up('close');
        if (!silent && !this._buttonClicked) {
            if (this._closeCallback) {
                this._closeCallback();
            }
        }
        this.$el.animate({opacity: 0.0, height: 0}, this._animationDelay, "swing", self.destroy.bind(self));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickButton: function (ev) {
        ev.preventDefault();
        if (this._buttonClicked) {
            return;
        }
        this._buttonClicked = true;
        var index = $(ev.currentTarget).index();
        var button = this.buttons[index];
        if (button.click) {
            button.click();
        }
        this.close(true);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClose: function (ev) {
        ev.preventDefault();
        this.close();
    },
});

return Notification;

});
