odoo.define('website.s_popup', function (require) {
'use strict';

const config = require('web.config');
const publicWidget = require('web.public.widget');

const PopupWidget = publicWidget.Widget.extend({
    selector: '.s_popup',
    events: {
        'click .s_popup_close': '_onCloseClick',
    },

    /**
     * @override
     */
    start: function () {
        this._bindPopup();
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        $(document).off('mouseleave.open_popup');
        clearTimeout(this.timeout);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _bindPopup: function () {
        const $main = this.$target.find('.s_popup_main');

        let display = $main.data('display');
        let delay = $main.data('showAfter');

        if (config.device.isMobile) {
            if (display === 'onExit') {
                display = 'afterDelay';
                delay = 5000;
            }
            this.$('.s_popup_main').removeClass('s_popup_center').addClass('s_popup_bottom');
        }

        if (display === 'afterDelay') {
            this.timeout = setTimeout(() => this._showPopup(), delay);
        } else {
            $(document).on('mouseleave.open_popup', () => this._showPopup());
        }
    },
    /**
     * @private
     */
    _hidePopup: function () {
        this.$target.find('.s_popup_main').addClass('d-none');
    },
    /**
     * @private
     */
    _showPopup: function () {
        this.$target.find('.s_popup_main').removeClass('d-none');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onCloseClick: function () {
        this._hidePopup();
    },
});

publicWidget.registry.popup = PopupWidget;

return PopupWidget;
});
