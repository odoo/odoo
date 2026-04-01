import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { renderToMarkup } from "@web/core/utils/render";
import { InputConfirmationDialog } from "@portal/js/components/input_confirmation_dialog/input_confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";

export class PortalSecurity extends Interaction {
    static selector = ".o_portal_security_body";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _modal: () => document.querySelector(".modal#portal_deactivate_account_modal"),
    };
    dynamicContent = {
        ".o_portal_new_api_key": {
            "t-on-click.prevent": this.onNewApiKeyClick,
        },
        ".o_portal_remove_api_key": {
            "t-on-click.prevent": this.onRemoveApiKeyClick,
        },
        _modal: {
            "t-on-hide.bs.modal.withTarget": (event, currentTargetEl) => {
                // Remove the error messages when we close the modal,
                // so when we re-open it again we get a fresh new form
                for (const el of currentTargetEl.querySelectorAll(".alert, .invalid-feedback")) {
                    el.remove();
                }
                for (const el of currentTargetEl.querySelectorAll(".is-invalid")) {
                    el.classList.remove("is-invalid");
                }
            },
        },
        // Defining what happens when you click the "Log out from all devices"
        // on the "/my/security" page.
        "#portal_revoke_all_sessions_popup": {
            "t-on-click": this.onRevokeAllSessionsClick,
        },
    };

    setup() {
        // Show the "deactivate your account" modal if needed
        const modalEl = document.querySelector(".modal.show#portal_deactivate_account_modal");
        if (modalEl) {
            modalEl.classList.remove("d-block");
            window.Modal.getOrCreateInstance(modalEl).show();
        }
    }

    async onNewApiKeyClick() {
        // This call is done just so it asks for the password confirmation before starting displaying the
        // dialog forms, to mimic the behavior from the backend, in which it asks for the password before
        // displaying the wizard.
        // The result of the call is unused. But it's required to call a method with the decorator `@check_identity`
        // in order to use `handleCheckIdentity`.
        await this.waitFor(
            handleCheckIdentity(
                this.waitFor(this.services.orm.call("res.users", "api_key_wizard", [user.userId])),
                this.services.orm,
                this.services.dialog
            )
        );

        const { duration } = await this.services.field.loadFields("res.users.apikeys.description", {
            fieldNames: ["duration"],
        });

        this.services.dialog.add(InputConfirmationDialog, {
            title: _t("New API Key"),
            body: renderToMarkup("portal.keydescription", {
                // Remove `'Custom Date'` selection for portal user
                duration_selection: duration.selection.filter((option) => option[0] !== "-1"),
            }),
            confirmLabel: _t("Confirm"),
            confirm: async ({ inputEl }) => {
                const formData = Object.fromEntries(new FormData(inputEl.closest("form")));
                const wizardId = await this.services.orm.create("res.users.apikeys.description", [{
                    name: formData['description'],
                    duration: formData['duration']
                }]);
                const res = await this.waitFor(
                    handleCheckIdentity(
                        this.waitFor(
                            this.services.orm.call("res.users.apikeys.description", "make_key", [
                                wizardId,
                            ])
                        ),
                        this.services.orm,
                        this.services.dialog
                    )
                );

                this.services.dialog.add(
                    ConfirmationDialog,
                    {
                        title: _t("API Key Ready"),
                        body: renderToMarkup("portal.keyshow", { key: res.context.default_key }),
                        confirmLabel: _t("Close"),
                    },
                    {
                        onClose: () => {
                            window.location.reload();
                        },
                    }
                );
            },
        });
    }
    async onRemoveApiKeyClick(ev) {
        await this.waitFor(
            await handleCheckIdentity(
                this.waitFor(
                    this.services.orm.call("res.users.apikeys", "remove", [parseInt(ev.target.id)])
                ),
                this.services.orm,
                this.services.dialog
            )
        );
        window.location.reload();
    }
    async onRevokeAllSessionsClick() {
        await this.waitFor(
            handleCheckIdentity(
                this.waitFor(
                    this.services.orm.call("res.users", "action_revoke_all_devices", [user.userId])
                ),
                this.services.orm,
                this.services.dialog
            )
        );
        window.location.reload();
        return true;
    }
}

registry.category("public.interactions").add("portal.portal_security", PortalSecurity);

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
        if (
            !(
                r &&
                r.type &&
                r.type === "ir.actions.act_window" &&
                r.res_model === "res.users.identitycheck"
            )
        ) {
            return r;
        }
        const checkId = r.res_id;
        return new Promise((resolve) => {
            ormService.write("res.users.identitycheck", [checkId], {auth_method: 'password'});
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
                    try {
                        result = await ormService.call("res.users.identitycheck", "run_check",
                            [ checkId ],
                            { 'context': {'password': inputEl.value} },
                        );
                    } catch {
                        inputEl.classList.add("is-invalid");
                        inputEl.setCustomValidity(_t("Check failed"));
                        inputEl.reportValidity();
                        return false;
                    }
                    resolve(result);
                    return true;
                },
                cancel: () => {},
                onInput: ({ inputEl }) => {
                    inputEl.classList.remove("is-invalid");
                    inputEl.setCustomValidity("");
                },
            });
        });
    });
}
