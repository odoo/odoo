import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { LeadGenerationDropdown } from "../../components/lead_generation_dropdown/lead_generation_dropdown";

export const crmListView = {
    ...listView,
    Controller: class extends listView.Controller {
        static components = {
            ...listView.Controller.components,
            LeadGenerationDropdown,
        }
    },
    buttonTemplate: "crm.List.Buttons",
};

registry.category("views").add("crm_list", crmListView);
