import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";

patch(FormController.prototype, {
    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        if (this.props.resModel === 'hr.applicant' && !this.model.root.data.job_id) {
            menuItems.addPropertyFieldValue.isAvailable = () => false;
        }
        return menuItems;
    },
});
