/** @odoo-module **/

import publicWidget from 'web.public.widget';

publicWidget.registry.WebsiteSaleGiftCardCopy = publicWidget.Widget.extend({
    selector: '.o_purchased_gift_card',
    /**
     * @override
     */
    start: function () {
        new ClipboardJS(this.$el.find('.copy-to-clipboard')[0]);
    }
});
