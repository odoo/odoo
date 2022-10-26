/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { StockPickingModel } from "@stock/views/picking_form/picking_form_model";
import { StockPickingFormController } from "@stock/views/picking_form/picking_form_controller";

export const StockPickingFormView = {
    ...formView,
    Controller: StockPickingFormController,
    Model: StockPickingModel,
};

registry.category("views").add("picking_form", StockPickingFormView);
