/** @odoo-module **/

import { Dialog } from "../core/dialog/dialog";
import { patch } from "@web/core/utils/patch";
import OwlDialog from "web.OwlDialog";

import { useEffect } from "@odoo/owl";

/**
 * This is a patch of the new Dialog class.
 * Its purpose is to inform the old "active/inactive" mechanism.
 */
patch(Dialog.prototype, "Legacy Adapted Dialog", {
    setup() {
        this._super();
        useEffect(
            () => {
                OwlDialog.display(this);
                return () => OwlDialog.hide(this);
            },
            () => []
        );
    },
});
