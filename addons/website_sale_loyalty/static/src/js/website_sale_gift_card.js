/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { browser } from '@web/core/browser/browser';

publicWidget.registry.WebsiteSaleGiftCardCopy = publicWidget.Widget.extend({
    selector: '.o_purchased_gift_card',
    events: {
        "click .copy-to-clipboard": "_onClickCopyToClipboard",
    },
    async _onClickCopyToClipboard(ev) {
        const textValue = ev.target.dataset.clipboardText;
        await browser.navigator.clipboard.writeText(textValue);
    },
});
