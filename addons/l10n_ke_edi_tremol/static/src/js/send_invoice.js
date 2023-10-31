odoo.define('l10n_ke_edi_tremol.action_post_send_invoice', function (require) {
    const core = require('web.core');
    const ajax = require('web.ajax');
    const Dialog = require('web.Dialog');
    var rpc = require('web.rpc');
    var _t = core._t;

    async function post_send(parent, {params}) {
        let refresh = false;
        for (let move_id in params.invoices) {
            try {
                const res = await ajax.post(
                    params.invoices[move_id].proxy_address + '/hw_proxy/l10n_ke_cu_send', {
                        messages: params.invoices[move_id].messages,
                        company_vat: params.invoices[move_id].company_vat
                    }
                );
                const res_obj = JSON.parse(res);
                if (res_obj.status === "ok") {
                    try {
                        await rpc.query({
                            model: 'account.move',
                            method: 'l10n_ke_cu_response',
                            args: [[], {'replies': res_obj.replies, 'serial_number': res_obj.serial_number, 'move_id': move_id}],
                        });
                        refresh = true;
                    } catch (e) {
                        Dialog.alert(this, _t("Error trying to connect to Odoo. Check your internet connection"));
                        break;
                    }
                } else {
                    Dialog.alert(this, _t("Posting an invoice has failed, with the message: \n") + res_obj.status);
                    break;
                }
            } catch(e) {
                Dialog.alert(this, _t("Error trying to connect to the middleware. Is the middleware running?"));
                break;
            }
        }
        if (refresh) {
            parent.services.action.doAction({
                'type': 'ir.actions.client',
                'tag': 'reload',
            });
        }
    }
    core.action_registry.add('post_send', post_send);
    return post_send;
});
