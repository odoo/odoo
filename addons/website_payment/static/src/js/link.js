odoo.define("website_payment.Link", function (require) {
    "use strict";

const Link = require("wysiwyg.widgets.Link");

Link.include({
    /**
     * @override
     */
    init() {
        this._super(...arguments);
        // 's_donation_donate_btn' prevents from changing link of 'Donate Now'
        //  anchor of Donation snippet.
        if (/(?:o_submit|s_donation_donate_btn)/.test(this.data.className)) {
            this.isButton = true;
        }
    }
});
});
