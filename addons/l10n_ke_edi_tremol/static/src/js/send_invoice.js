odoo.define('l10n_ke_edi_tremol.action_post_send_invoice', function (require) {
    const core = require('web.core');
    const ajax = require('web.ajax');
    const Dialog = require('web.Dialog');
    var rpc = require('web.rpc');
    var _t = core._t;

    async function post_send(parent, {params}) {
        const move_id = params.move_id;
        await ajax.post(params.proxy_address + '/hw_proxy/l10n_ke_cu_send', params).then(function (res) {
            const res_obj = JSON.parse(res);
            if (res_obj.status != "ok") {
                Dialog.alert(this, "Posting the invoice has failed, with the message: \n" + res_obj.status);
            } else {
                rpc.query({
                    model: 'account.move',
                    method: 'l10n_ke_cu_response',
                    args: [[], {'replies': res_obj.replies, 'serial_number': res_obj.serial_number, 'move_id': move_id}],
                }).then(function () {
                    parent.services.action.doAction({
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                    });
                }, function () {
                    Dialog.alert(this, _t("Error trying to connect to Odoo. Check your internet connection"));
                })
            }
        }, function () {
            Dialog.alert(this, _t("Error trying to connect to the middleware. Is the middleware running?"));
        })
    }
    core.action_registry.add('post_send', post_send);
    return post_send;
});
