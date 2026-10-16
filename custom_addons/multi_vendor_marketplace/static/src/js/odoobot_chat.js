odoo.define('multi_vendor_marketplace.odoobot_chat', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    
    publicWidget.registry.OdooBotChat = publicWidget.Widget.extend({
        selector: '#o_product_terms_and_share',
        events: {
            'click #o_livechat_button': '_onChatButtonClick',
        },

        /**
         * @override
         */
        start: function () {
            return this._super.apply(this, arguments);
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * Handle click on chat button
         *
         * @private
         * @param {Event} ev
         */
        _onChatButtonClick: function (ev) {
            ev.preventDefault();
            if (window.livechatButton) {
                window.livechatButton.onClick();
            }
        }
    });

    return publicWidget.registry.OdooBotChat;
}); 