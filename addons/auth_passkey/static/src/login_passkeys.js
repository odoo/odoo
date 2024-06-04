/** @odoo-module **/

import { jsonrpc } from "@web/core/network/rpc_service";
import publicWidget from "@web/legacy/js/public/public_widget";
import { startAuthentication } from "../lib/simplewebauthn.js";

publicWidget.registry.passkeyLogin = publicWidget.Widget.extend({
    selector: '.passkey_login_link',
    events: { 'click': '_onclick' },

    _onclick: async function() {
        const serverOptions = await jsonrpc("/auth/passkey/start-auth");
        const auth = await startAuthentication(serverOptions).catch(e => console.error(e));
        if(!auth) return false;
        const form = document.querySelector('form[class="oe_login_form"]');
        form.querySelector('input[name="webauthn_response"]').value = JSON.stringify(auth);
        form.querySelector('input[name="type"]').value = 'webauthn';
        form.submit();
    }
})
