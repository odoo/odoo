/** @odoo-module native */

import { FormController } from "@web/views/form";
import { patch } from "@web/core/utils/patch";

patch(FormController.prototype, {
    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        if (
            this.props.resModel === "account.asset" &&
            this.model.root.data.state === "model"
        ) {
            menuItems.addPropertyFieldValue.isAvailable = () => false;
        }
        return menuItems;
    },
});
