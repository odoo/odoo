import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("team_board_contact_methods").add(
    "copyEmail",
    {
        label: _t("Copy email"),
        loadingLabel: _t("Copying..."),
        errorMessage: _t("Could not copy the email."),
        async run({ interaction, memberEl }) {
            const memberEmail = memberEl?.dataset.memberEmail;
            if (!memberEmail) {
                throw new Error("missing_member_email");
            }
            const writeText =
                interaction.el.ownerDocument.defaultView?.navigator.clipboard?.writeText;
            if (!writeText) {
                throw new Error("clipboard_not_supported");
            }
            await writeText.call(
                interaction.el.ownerDocument.defaultView.navigator.clipboard,
                memberEmail
            );
            return {
                successMessage: _t("Email copied."),
            };
        },
    },
    { sequence: 20 }
);
