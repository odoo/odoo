import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("website.team_board.contact_methods").add("copy_email", {
    label: _t("Copy email"),
    sequence: 20,
    className: "btn-outline-secondary",
    async handler({ member, services }) {
        if (!member.name) {
            return;
        }
        const normalizedName = member.name.toLowerCase().trim().replace(/\s+/g, ".");
        const email = `${normalizedName}@example.com`;
        try {
            await navigator.clipboard.writeText(email);
            services.notification.add(_t("Email copied: %s", email), {
                type: "success",
            });
        } catch {
            services.notification.add(_t("Could not copy the email to the clipboard."), {
                type: "danger",
            });
        }
    },
});
