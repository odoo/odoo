/** @odoo-module **/
import {Trip} from "@web_help/trip.esm";
import {registry} from "@web/core/registry";

export class UserTrip extends Trip {
    setup() {
        this.addStep({
            selector: ".o_list_button_add, .o-kanban-button-new",
            content: this.env._t("To create a new user click here."),
        });

        this.addStep({
            selector: ".o_cp_searchview, .o_enable_searchview",
            content: this.env._t("Use the searchbar to find specific users."),
            renderContext: {
                cbBtnText: this.env._t("Next"),
                closeBtnText: this.env._t("Cancel"),
            },
        });

        this.addStep({
            selector: ".o_cp_switch_buttons",
            content: this.env._t("You can switch to different views here."),
        });
    }
}

registry.category("trips").add("user_trip", {
    Trip: UserTrip,
    selector: (model, viewType) =>
        model === "res.users" && ["list", "kanban"].includes(viewType),
});
