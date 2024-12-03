/** @odoo-module **/

import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';
import { renderToMarkup } from "@web/core/utils/render";
import publicWidget from '@web/legacy/js/public/public_widget';
import { InputConfirmationDialog } from './components/input_confirmation_dialog/input_confirmation_dialog';
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";

publicWidget.registry.NewAPIKeyButton = publicWidget.Widget.extend({
    selector: '.o_portal_new_api_key',
    events: {
        click: '_onClick'
    },

    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
        this.dialog = this.bindService("dialog");
    },

    async _onClick(e){
        e.preventDefault();
        // This call is done just so it asks for the password confirmation before starting displaying the
        // dialog forms, to mimic the behavior from the backend, in which it asks for the password before
        // displaying the wizard.
        // The result of the call is unused. But it's required to call a method with the decorator `@check_identity`
        // in order to use `handleCheckIdentity`.
        await handleCheckIdentity(
            this.orm.call("res.users", "api_key_wizard", [user.userId]),
            this.orm,
            this.dialog
        );

        this.call("dialog", "add", InputConfirmationDialog, {
            title: _t("New API Key"),
            body: renderToMarkup("portal.keydescription"),
            confirmLabel: _t("Confirm"),
            confirm: async ({ inputEl }) => {
                const description = inputEl.value;
                const wizard_id = await this.orm.create("res.users.apikeys.description", [{ name: description }]);
                const res = await handleCheckIdentity(
                    this.orm.call("res.users.apikeys.description", "make_key", [wizard_id]),
                    this.orm,
                    this.dialog
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

    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
        this.dialog = this.bindService("dialog");
    },

    async _onClick(e){
        e.preventDefault();
        await handleCheckIdentity(
            this.orm.call("res.users.apikeys", "remove", [parseInt(this.el.id)]),
            this.orm,
            this.dialog
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

    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
        this.dialog = this.bindService("dialog")
    },

    async _onClick() {
        await handleCheckIdentity(
            this.orm.call("res.users", "action_revoke_all_devices", [user.userId]),
            this.orm,
            this.dialog
        );
        window.location = window.location;
        return true;
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
                cancel: () => {},
                onInput: ({ inputEl }) => {
                    inputEl.classList.remove("is-invalid");
                    inputEl.setCustomValidity("");
                },
            });
        });
    });
}
