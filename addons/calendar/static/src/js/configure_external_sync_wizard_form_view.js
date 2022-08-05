/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { ConfigureExternalSyncWizardFormRenderer } from "./configure_external_sync_wizard_form_renderer";


export const ConfigureExternalSyncWizardFormView = {
    ...formView,
    Renderer: ConfigureExternalSyncWizardFormRenderer,
};

registry.category("views").add("configure_external_sync_wizard", ConfigureExternalSyncWizardFormView);
