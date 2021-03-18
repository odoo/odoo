odoo.define('website_sale_gift_card.website_sale_gift_card', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');

    publicWidget.registry.WebsiteSaleGiftCard = publicWidget.Widget.extend({
            selector: '.oe_website_sale_gift_card',
            events: {
                'click .js_show_gift_card': '_onShowGiftCardClick',
            },
            /**
             * @private
             * @param {Event} ev
             */
            _onShowGiftCardClick: function (ev) {
                $(ev.currentTarget).hide();
                this.$('.gift_card_form').removeClass('d-none');
            }
        }
    )
    publicWidget.registry.WebsiteSaleGiftCardCopy = publicWidget.Widget.extend({
        selector: '.o_purchased_gift_card',
        /**
         * @override
         */
        start: function () {
            new ClipboardJS(this.$el.find('.copy-to-clipboard')[0]);
        }
    })
})
