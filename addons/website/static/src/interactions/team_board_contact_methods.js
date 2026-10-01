import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("website.team_board_contact_methods").add("copy_email", {
    label: _t("Copy Email"),
    async onClick({ name, notification }) {
        const email = `${name.toLowerCase().replaceAll(" ", ".")}@test.test`;
        try {
            await window.navigator.clipboard.writeText(email);
            notification.add(_t("Email copied."), { type: "success" });
        } catch {
            notification.add(_t("Could not copy the email."), { type: "danger" });
        }
    },
});
