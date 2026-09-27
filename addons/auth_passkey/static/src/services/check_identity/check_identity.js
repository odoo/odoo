import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { CheckIdentityForm } from "@web/core/session/check_identity";

import * as passkeyLib from "@auth_passkey/../lib/simplewebauthn";

patch(CheckIdentityForm.prototype, {
    async setup() {
        super.setup();
        this.authMethodTemplates = {
            ...this.authMethodTemplates,
            webauthn: {
                form: "auth_passkey.CheckIdentityFormWebAuthN",
                linkString: "auth_passkey.CheckIdentityLinkStringWebAuthN",
            },
        };
    },
    async onSubmit(ev) {
        const form = ev.target;
        if (form.querySelector('input[name="type"]').value === "webauthn") {
            const serverOptions = await rpc("/auth/passkey/start-auth");
            const auth = await passkeyLib.startAuthentication(serverOptions).catch((e) => console.log(e));
            if (!auth) {
                return false;
            }
            form.querySelector('input[name="webauthn_response"]').value = JSON.stringify(auth);
        }
        super.onSubmit(ev);
    },
});
