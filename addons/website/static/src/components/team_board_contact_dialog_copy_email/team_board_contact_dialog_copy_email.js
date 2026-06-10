import { _t } from "@web/core/l10n/translation";
import { contactActionRegistry } from "../team_board_contact_dialog/team_board_contact_dialog";

contactActionRegistry.add("copy_email", {
    label: _t("Copy email"),
    sequence: 1,
    primary: false,
    execute: async (_, component) => {
        try {
            await navigator.clipboard.writeText("jupir@odoo.com");
            component.notifications.add("Email address copied", { type: "success" });
        } catch (error) {
            console.error(error);
            component.notifications.add("Could no copy the email address", { type: "danger" });
        }
    },
});
