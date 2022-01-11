/** @odoo-module **/

import { PortalWizardUserListRenderer } from "../list/portal_wizard_user_list_renderer";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { registry } from "@web/core/registry";

export class PortalUserX2ManyField extends X2ManyField {
    setup() {
        super.setup();
        this.Renderer = PortalWizardUserListRenderer;
    }
}

registry.category("fields").add("portal_wizard_user_one2many", PortalUserX2ManyField);
