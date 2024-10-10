odoo.define("website_payment.wysiwyg", function (require) {
    "use strict";

const Wysiwyg = require("web_editor.wysiwyg");

Wysiwyg.include({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    /**
     * @override
     */
    removeLink() {
        if (this.lastElement.classList.contains("s_donation_donate_btn")) {
            return;
        }
        this._super(...arguments);
    },
});
});
