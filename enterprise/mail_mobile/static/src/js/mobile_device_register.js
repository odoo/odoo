/** @odoo-module **/

import mobile from "@web_mobile/js/services/core";
import { rpc } from "@web/core/network/rpc";
import { session } from "@web/session";

//Send info only if client is mobile
if (mobile.methods.getFCMKey) {
    var registerDevice = function (fcm_project_id) {
        mobile.methods.getFCMKey({
            project_id: fcm_project_id,
            inbox_action: session.inbox_action,
        }).then(function (response) {
            if (response.success) {
                rpc('/web/dataset/call_kw/res.config.settings/register_device', {
                    model: 'res.config.settings',
                    method: 'register_device',
                    args: [
                        response.data.subscription_id,
                        response.data.device_name,
                        response.data.fcm_token_old,
                    ],
                    kwargs: {},
                }).then(function (ocn_token) {
                    if (mobile.methods.setOCNToken) {
                        mobile.methods.setOCNToken({ocn_token: ocn_token});
                    }
                });
            }
        }).catch(e => console.error(e));
    };
    if (session.fcm_project_id) {
        registerDevice(session.fcm_project_id);
    } else {
        rpc('/web/dataset/call_kw/res.config.settings/get_fcm_project_id', {
            model: 'res.config.settings',
            method: 'get_fcm_project_id',
            args: [],
            kwargs: {},
        }).then(function (response) {
            if (response) {
                registerDevice(response);
            }
        });
    }
}
