import { renderToMarkup } from "@web/core/utils/render";
import { InputConfirmationDialog } from "../js/components/input_confirmation_dialog/input_confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

/**
 * Wraps an RPC call in a check for the result being an identity check action
 * descriptor. If no such result is found, just returns the wrapped promise's
 * result as-is; otherwise shows an identity check dialog and resumes the call
 * on success.
 *
 * Warning: does not in and of itself trigger an identity check, a promise which
 * never triggers and identity check internally will do nothing of use.
 *
 * @param {Promise} wrapped promise to check for an identity check request
 * @param {Function} ormService bound do the widget
 * @param {Function} dialogService dialog service
 * @returns {Promise} result of the original call
 */
export async function handleCheckIdentity(wrapped, ormService, dialogService) {
    return wrapped.then((r) => {
        if (!(r.type && r.type === "ir.actions.act_window" && r.res_model === "res.users.identitycheck")) {
            return r;
        }
        const checkId = r.res_id;
        return new Promise((resolve) => {
            dialogService.add(InputConfirmationDialog, {
                title: _t("Security Control"),
                body: renderToMarkup("portal.identitycheck"),
                confirmLabel: _t("Confirm Password"),
                confirm: async ({ inputEl }) => {
                    if (!inputEl.reportValidity()) {
                        inputEl.classList.add("is-invalid");
                        return false;
                    }
                    let result;
                    await ormService.write("res.users.identitycheck", [checkId], { password: inputEl.value });
                    try {
                        result = await ormService.call("res.users.identitycheck", "run_check", [checkId]);
                    } catch {
                        inputEl.classList.add("is-invalid");
                        inputEl.setCustomValidity(_t("Check failed"));
                        inputEl.reportValidity();
                        return false;
                    }
                    resolve(result);
                    return true;
                },
                cancel: () => { },
                onInput: ({ inputEl }) => {
                    inputEl.classList.remove("is-invalid");
                    inputEl.setCustomValidity("");
                },
            });
        });
    });
}
