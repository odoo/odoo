import { ErrorDialog } from "@web/core/errors/error_dialogs";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

function turnstileErrorHandler(env, error) {
    if (error.message.includes("Turnstile Error")) {
        env.services.dialog.add(ErrorDialog, {
            name: _t("Cloudflare Turnstile Error"),
            traceback: _t(
                `There was an error with Cloudflare Turnstile, the captcha system.\n` +
                `Please make sure your credentials for this service are properly set up.\n` +
                `The error code is: %s.\n` +
                `You can find more information about this error code here: https://developers.cloudflare.com/turnstile/reference/errors.`,
                error.event.error.code
            ),
        });
        return true;
    }
}

registry.category("error_handlers").add("turnstile_error_handler", turnstileErrorHandler);
