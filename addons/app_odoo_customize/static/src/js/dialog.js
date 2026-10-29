/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

patch(Dialog.prototype, "app_odoo_customize.Dialog", {
    setup() {
        this._super.apply(this, arguments);
        const app_system_name = session.app_system_name || "odooAi";
        this.title = app_system_name;
        owl.onMounted(() => {
            this.setDrag();
        });
    },
    setDrag() {
        var $dl = $('#' + this.id + ' .modal-dialog .modal-content');
        if ($dl)
            $dl.draggable({
                handle: ".modal-header"
            });
    },
});

