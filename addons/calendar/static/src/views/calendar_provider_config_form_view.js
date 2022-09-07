/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { CalendarProviderConfigFormRenderer } from "./calendar_provider_config_form_renderer";


export const CalendarProviderConfigFormView = {
    ...formView,
    Renderer: CalendarProviderConfigFormRenderer,
};

registry.category("views").add("calendar_provider_config_form", CalendarProviderConfigFormView);
