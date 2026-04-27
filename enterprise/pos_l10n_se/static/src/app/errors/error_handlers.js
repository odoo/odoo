import { registry } from "@web/core/registry";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

export class SwedenBlackboxError extends Error {}

function swedenBlackboxErrorHandler(env, error, originalError) {
    if (originalError instanceof SwedenBlackboxError) {
        env.services.dialog.add(AlertDialog, {
            title: _t("Blackbox Error"),
            body: originalError.message,
        });
        return true;
    }
    return false;
}
registry.category("error_handlers").add("swedenBlackboxErrorHandler", swedenBlackboxErrorHandler);
