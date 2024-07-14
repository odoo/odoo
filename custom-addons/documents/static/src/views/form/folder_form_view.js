/** @odoo-module */

import { registry } from "@web/core/registry";
import { formView } from '@web/views/form/form_view';
import { FolderFormController } from "./folder_form_controller";

export const FolderFormView = {
    ...formView,
    Controller: FolderFormController,
};

registry.category("views").add("folder_form", FolderFormView);
