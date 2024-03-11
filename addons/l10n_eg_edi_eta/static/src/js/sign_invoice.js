odoo.define('l10n_eg_edi_eta.action_post_sign_invoice', function (require) {
    const core = require('web.core');
    const ajax = require('web.ajax');
    const Dialog = require('web.Dialog');
    var rpc = require('web.rpc');
    var _t = core._t;

    function get_drive_error(value) {
        switch(value) {
           case 'no_pykcs11': return _t("Missing library - Please make sure that PyKCS11 is correctly installed on the local proxy server");
           case 'missing_dll': return _t("Missing Dependency - If you are using Windows, make sure eps2003csp11.dll is correctly installed. You can download it here: https://www.egypttrust.com/en/downloads/other-drivers. If you are using Linux or macOS, please install OpenSC");
           case 'no_drive': return _t("No drive found - Make sure the thumb drive is correctly inserted");
           case 'multiple_drive': return _t("Multiple drive detected - Only one secure thumb drive can be inserted at the same time");
           case 'system_unsupported': return _t("System not supported");
           case 'unauthorized': return _t("Unauthorized");
        }
        return _t("Unexpected error:") + value;

    }

    async function action_get_drive_certificate(parent, {params}) {
        const host = params.sign_host;
        const drive_id = params.drive_id;
        delete params.sign_host;
        delete params.drive_id;
        await ajax.post(host + '/hw_l10n_eg_eta/certificate', params).then(function (res) {
            const res_obj = JSON.parse(res);
            if (res_obj.error) {
                Dialog.alert(this, get_drive_error(res_obj.error));
            } else if (res_obj.certificate) {
                rpc.query({
                    model: 'l10n_eg_edi.thumb.drive',
                    method: 'set_certificate',
                    args: [[drive_id], res_obj.certificate],
                }).then(function () {
                    parent.services.action.doAction({
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                    });
                }, function () {
                    Dialog.alert(this, _t("Error trying to connect to Odoo. Check your internet connection"));
                })

            } else {
                Dialog.alert(this, _t('An unexpected error has occurred'));
            }
        }, function () {
            Dialog.alert(this, _t("Error trying to connect to the middleware. Is the middleware running?"));
        })
    }

    async function action_post_sign_invoice(parent, {params}) {
        const host = params.sign_host;
        const drive_id = params.drive_id;
        delete params.sign_host;
        delete params.drive_id;
        await ajax.post(host + '/hw_l10n_eg_eta/sign', params).then(function (res) {
            const res_obj = JSON.parse(res);
            if (res_obj.error) {
                Dialog.alert(this, get_drive_error(res_obj.error));
            } else if (res_obj.invoices) {
                rpc.query({
                    model: 'l10n_eg_edi.thumb.drive',
                    method: 'set_signature_data',
                    args: [[drive_id], res_obj.invoices],
                }).then(function () {
                    parent.services.action.doAction({
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                    });
                }, function () {
                    Dialog.alert(this, _t("Error trying to connect to Odoo. Check your internet connection"));
                })

            } else {
                Dialog.alert(this, _t('An unexpected error has occurred'));
            }
        }, function () {
            Dialog.alert(this, _t("Error trying to connect to the middleware. Is the middleware running?"));
        })
    }

    core.action_registry.add('action_get_drive_certificate', action_get_drive_certificate);
    core.action_registry.add('action_post_sign_invoice', action_post_sign_invoice);

    return action_post_sign_invoice;
});
