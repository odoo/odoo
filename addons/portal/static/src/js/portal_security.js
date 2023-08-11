/** @odoo-module **/

import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';
import { renderToMarkup } from "@web/core/utils/render";
import publicWidget from '@web/legacy/js/public/public_widget';
import { session } from "@web/session";
import { InputConfirmationDialog } from './components/input_confirmation_dialog/input_confirmation_dialog';
import { _t } from "@web/core/l10n/translation";

publicWidget.registry.NewAPIKeyButton = publicWidget.Widget.extend({
    selector: '.o_portal_new_api_key',
    events: {
        click: '_onClick'
    },

    async _onClick(e){
        e.preventDefault();
        // This call is done just so it asks for the password confirmation before starting displaying the
        // dialog forms, to mimic the behavior from the backend, in which it asks for the password before
        // displaying the wizard.
        // The result of the call is unused. But it's required to call a method with the decorator `@check_identity`
        // in order to use `handleCheckIdentity`.
        await handleCheckIdentity(this.proxy('_rpc'), this._rpc({
            model: 'res.users',
            method: 'api_key_wizard',
            args: [session.user_id],
        }), (...args) => this.call("dialog", "add", ...args));

        this.call("dialog", "add", InputConfirmationDialog, {
            title: _t("New API Key"),
            body: renderToMarkup("portal.keydescription"),
            confirmLabel: _t("Confirm"),
            confirm: async ({ inputEl }) => {
                const description = inputEl.value;
                const wizard_id = await this._rpc({
                    model: "res.users.apikeys.description",
                    method: "create",
                    args: [{ name: description }],
                });
                const res = await handleCheckIdentity(
                    this.proxy('_rpc'),
                    this._rpc({
                        model: 'res.users.apikeys.description',
                        method: 'make_key',
                        args: [wizard_id],
                    }),
                    (...args) => this.call("dialog", "add", ...args)
                );

                this.call("dialog", "add", ConfirmationDialog, {
                    title: _t("API Key Ready"),
                    body: renderToMarkup("portal.keyshow", { key: res.context.default_key }),
                    confirmLabel: _t("Close"),
                }, {
                    onClose: () => {
                        window.location = window.location;
                    },
                })
            }
        });
    }
});

publicWidget.registry.RemoveAPIKeyButton = publicWidget.Widget.extend({
    selector: '.o_portal_remove_api_key',
    events: {
        click: '_onClick'
    },

    async _onClick(e){
        e.preventDefault();
        await handleCheckIdentity(
            this.proxy('_rpc'),
            this._rpc({
                model: 'res.users.apikeys',
                method: 'remove',
                args: [parseInt(this.el.id)]
            }),
            (...args) => this.call("dialog", "add", ...args)
        );
        window.location = window.location;
    }
});

publicWidget.registry.portalSecurity = publicWidget.Widget.extend({
    selector: '.o_portal_security_body',

    /**
     * @override
     */
    init: function () {
        // Show the "deactivate your account" modal if needed
        $('.modal.show#portal_deactivate_account_modal').removeClass('d-block').modal('show');

        // Remove the error messages when we close the modal,
        // so when we re-open it again we get a fresh new form
        $('.modal#portal_deactivate_account_modal').on('hide.bs.modal', (event) => {
            const $target = $(event.currentTarget);
            $target.find('.alert').remove();
            $target.find('.invalid-feedback').remove();
            $target.find('.is-invalid').removeClass('is-invalid');
        });

        return this._super(...arguments);
    },

});

/**
 * Defining what happens when you click the "Log out from all devices"
 * on the "/my/security" page.
 */
publicWidget.registry.RevokeSessionsButton = publicWidget.Widget.extend({
    selector: '#portal_revoke_all_sessions_popup',
    events: {
        click: '_onClick',
    },

    async _onClick() {
        const { res_id: checkId } = await this._rpc({
            model: 'res.users',
            method: 'api_key_wizard',
            args: [session.user_id],
        });
        this.call("dialog", "add", InputConfirmationDialog, {
            title: _t("Log out from all devices?"),
            body: renderToMarkup("portal.revoke_all_devices_popup_template"),
            confirmLabel: _t("Log out from all devices"),
            confirm: async ({ inputEl }) => {
                if (!inputEl.reportValidity()) {
                    inputEl.classList.add("is-invalid");
                    return false;
                }

                await this._rpc({
                    model: "res.users.identitycheck",
                    method: "write",
                    args: [checkId, { password: inputEl.value }],
                });
                try {
                    await this._rpc({
                        model: "res.users.identitycheck",
                        method: "revoke_all_devices",
                        args: [checkId],
                    });
                } catch {
                    inputEl.classList.add("is-invalid");
                    inputEl.setCustomValidity(_t("Check failed"));
                    inputEl.reportValidity();
                    return false;
                }

                window.location.href = "/web/session/logout?redirect=/";
                return true;
            },
            cancel: () => {},
            onInput: ({ inputEl }) => {
                inputEl.classList.remove("is-invalid");
                inputEl.setCustomValidity("");
            },
        });
    },
});

/**
 * Wraps an RPC call in a check for the result being an identity check action
 * descriptor. If no such result is found, just returns the wrapped promise's
 * result as-is; otherwise shows an identity check dialog and resumes the call
 * on success.
 *
 * Warning: does not in and of itself trigger an identity check, a promise which
 * never triggers and identity check internally will do nothing of use.
 *
 * @param {Function} rpc Widget#_rpc bound do the widget
 * @param {Promise} wrapped promise to check for an identity check request
 * @param {Function} addDialog add a dialog to the dialog service
 * @returns {Promise} result of the original call
 */
export async function handleCheckIdentity(rpc, wrapped, addDialog) {
    return wrapped.then((r) => {
        if (!(r.type === "ir.actions.act_window" && r.res_model === "res.users.identitycheck")) {
            return r;
        }
        const checkId = r.res_id;
        return new Promise((resolve) => {
            addDialog(InputConfirmationDialog, {
                title: _t("Security Control"),
                body: renderToMarkup("portal.identitycheck"),
                confirmLabel: _t("Confirm Password"),
                confirm: async ({ inputEl }) => {
                    if (!inputEl.reportValidity()) {
                        inputEl.classList.add("is-invalid");
                        return false;
                    }
                    let result;
                    await rpc({
                        model: "res.users.identitycheck",
                        method: "write",
                        args: [checkId, { password: inputEl.value }],
                    });
                    try {
                        result = await rpc({
                            model: "res.users.identitycheck",
                            method: "run_check",
                            args: [checkId],
                        });
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
