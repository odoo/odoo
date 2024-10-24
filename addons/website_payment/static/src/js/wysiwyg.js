/** @odoo-module **/

import Wysiwyg from "web_editor.wysiwyg";

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
