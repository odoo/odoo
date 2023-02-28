/** @odoo-module alias=portal.security **/

import publicWidget from "web.public.widget";
import Dialog from "web.Dialog";
import {_t, qweb} from "web.core";
import session from "web.session";

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
        }));
        const self = this;
        const d_description = new Dialog(self, {
            title: _t('New API Key'),
            $content: qweb.render('portal.keydescription'),
            buttons: [{text: _t('Confirm'), classes: 'btn-primary', close: true, click: async () => {
                var description = d_description.el.querySelector('[name="description"]').value;
                var wizard_id = await this._rpc({
                    model: 'res.users.apikeys.description',
                    method: 'create',
                    args: [{name: description}],
                });
                var res = await handleCheckIdentity(
                    this.proxy('_rpc'),
                    this._rpc({
                        model: 'res.users.apikeys.description',
                        method: 'make_key',
                        args: [wizard_id],
                    })
                );
                const d_show = new Dialog(self, {
                    title: _t('API Key Ready'),
                    $content: qweb.render('portal.keyshow', {key: res.context.default_key}),
                    buttons: [{text: _t('Close'), clases: 'btn-primary', close: true}],
                });
                d_show.on('closed', this, () => {
                    window.location = window.location;
                });
                d_show.open();
            }}, {text: _t('Discard'), close: true}],
        });
        d_description.opened(() => {
            const input = d_description.el.querySelector('[name="description"]');
            input.focus();
            d_description.el.addEventListener('submit', (e) => {
                e.preventDefault();
                d_description.$footer.find('.btn-primary').click();
            });
        });
        d_description.open();
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
            })
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
        const rpc = this.proxy('_rpc');
        const wrapped = this._rpc({
            model: 'res.users',
            method: 'api_key_wizard',
            args: [session.user_id],
        });
        await handleRevokeSessions(rpc, wrapped);
        window.location.href = "/web/session/logout?redirect=/";

        function handleRevokeSessions(rpc, wrapped) {
            return wrapped.then((inst) => {
                const check_id = inst.res_id
                var $content = $(qweb.render("portal.revoke_all_devices_popup_template"));
                return new Promise((resolve) => {
                    var dialog = new Dialog(this, {
                        title: _t("Log out from all devices?"),
                        $content,
                        buttons: [{
                            text: _t("Log out from all devices"), classes: 'btn btn-primary',
                            // nb: if click & close, waits for click to resolve before closing
                            async click() {
                                const password_input = this.el.querySelector('[name=password]');
                                if (!password_input.reportValidity()) {
                                    password_input.classList.add('is-invalid');
                                    return;
                                };
                                await rpc({
                                    model: 'res.users.identitycheck',
                                    method: 'write',
                                    args: [check_id, {password: password_input.value}]
                                });
                                await rpc({
                                    model: 'res.users.identitycheck',
                                    method: 'revoke_all_devices',
                                    args: [check_id]
                                }).then((inst) => {
                                    this.close();
                                    resolve(inst);
                                }, (err) => {
                                    err.event.preventDefault(); // suppress crashmanager
                                    password_input.classList.add('is-invalid');
                                    password_input.setCustomValidity(_t("Check failed"));
                                    password_input.reportValidity();
                                });
                            }
                        }, {
                            text: _t('Cancel'), close: true
                        }] 
                    });
                    dialog.opened(() => {
                        const password_input = dialog.el.querySelector('[name="password"]');
                        password_input.focus();
                        password_input.addEventListener('input', () => {
                            password_input.classList.remove('is-invalid');
                            password_input.setCustomValidity('');
                        });
                        dialog.el.addEventListener('submit', (e) => {
                            e.preventDefault();
                            dialog.$footer.find('.btn-primary').click();
                        });
                    });
                dialog.open();
                })
            })
        }
    }
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
 * @returns {Promise} result of the original call
 */
function handleCheckIdentity(rpc, wrapped) {
    return wrapped.then((r) => {
        if (!(r.type === "ir.actions.act_window" && r.res_model === "res.users.identitycheck")) {
            return r;
        }
        const check_id = r.res_id;
        return new Promise((resolve, reject) => {
            const d = new Dialog(null, {
                title: _t("Security Control"),
                $content: qweb.render('portal.identitycheck'),
                buttons: [{
                    text: _t("Confirm Password"), classes: 'btn btn-primary',
                    // nb: if click & close, waits for click to resolve before closing
                    click() {
                        const password_input = this.el.querySelector('[name=password]');
                        if (!password_input.reportValidity()) {
                            password_input.classList.add('is-invalid');
                            return;
                        }
                        return rpc({
                            model: 'res.users.identitycheck',
                            method: 'write',
                            args: [check_id, {password: password_input.value}]
                        }).then(() => rpc({
                            model: 'res.users.identitycheck',
                            method: 'run_check',
                            args: [check_id]
                        })).then((r) => {
                            this.close();
                            resolve(r);
                        }, (err) => {
                            err.event.preventDefault(); // suppress crashmanager
                            password_input.classList.add('is-invalid');
                            password_input.setCustomValidity(_t("Check failed"));
                            password_input.reportValidity();
                        });
                    }
                }, {
                    text: _t('Cancel'), close: true
                }]
            }).on('close', null, () => {
                // unlink wizard object?
                reject();
            });
            d.opened(() => {
                const pw = d.el.querySelector('[name="password"]');
                pw.focus();
                pw.addEventListener('input', () => {
                    pw.classList.remove('is-invalid');
                    pw.setCustomValidity('');
                });
                d.el.addEventListener('submit', (e) => {
                    e.preventDefault();
                    d.$footer.find('.btn-primary').click();
                });
            });
            d.open();
        });
    });
}
export default {
    handleCheckIdentity,
}
