/** @odoo-module */

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { HelpdeskTeamController } from "./helpdesk_team_form_controller";

registry.category("views").add("helpdesk_team_form", {
    ...formView,
    Controller: HelpdeskTeamController,
});
