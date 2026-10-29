import {
    AggregateEmailImageError,
    EmailImageError,
} from "@mail/editor/plugins/email_image_format_plugin";
import { UncaughtPromiseError } from "@web/core/errors/error_service";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * @param {OdooEnv} env
 * @param {UncaughError} error
 * @param {Error} originalError
 * @returns {boolean}
 */
export function emailImageErrorHandler(env, error, originalError) {
    if (!(error instanceof UncaughtPromiseError)) {
        return false;
    }
    const notification = useService("notification");
    if (
        originalError instanceof EmailImageError ||
        originalError instanceof AggregateEmailImageError
    ) {
        notification.add(_t("Image processing error, try saving again or re-upload them."), {
            type: "danger",
            sticky: true,
        });
        return true;
    }
    return false;
}

registry.category("error_handlers").add("emailImageErrorHandler", emailImageErrorHandler);
