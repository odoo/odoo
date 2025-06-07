/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";


class PickingFormController extends FormController {
    static template = "mrp_subcontracting.PickingFormController";
}

const PickingFormView = {
    ...formView,
    Controller: PickingFormController,
};

registry.category("views").add("subcontracting_portal_picking_form_view", PickingFormView);
