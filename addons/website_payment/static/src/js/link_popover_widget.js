/** @odoo-module **/

import weWidgets from "wysiwyg.widgets";
import {_t} from "web.core";

weWidgets.LinkPopoverWidget.include({
    /**
     * @override
     */
    start() {
        // Disable "edit link" & remove link" buttons in link popover.
        if (this.target.classList.contains("s_donation_donate_btn")) {
            this.el.querySelectorAll(".o_we_edit_link, .o_we_remove_link").forEach((anchor) => {
                anchor.style.cursor = "default";
                anchor.classList.add("text-muted", "o_disable_link");
                anchor.classList.remove("text-dark");
                anchor.setAttribute("title", _t("This button is dynamic and linked to the form, it cannot be updated."));
            });
        }

        return this._super(...arguments);
    },
});
