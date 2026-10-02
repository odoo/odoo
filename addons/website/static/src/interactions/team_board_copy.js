import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("website.s_team_board.button_methods").add(
    "copy_name",
    {
        label: _t("Copy name"),
        successMessage: _t("Name copied."),
        errorMessage: _t("Could not copy the name."),
        closeOnSuccess: false,
        async onClick({ memberName }) {
            await navigator.clipboard.writeText(memberName);
        },
    },
    { sequence: 20 }
);
