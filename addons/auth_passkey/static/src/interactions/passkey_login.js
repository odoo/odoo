import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { rpc } from "@web/core/network/rpc";
import { startAuthentication } from "../../lib/simplewebauthn.js";

export class PasskeyLogin extends Interaction {
    static selector = ".passkey_login_link";
    dynamicContent = {
        _root: { "t-on-click": this.onClick },
    };

    async onClick() {
        const serverOptions = await this.waitFor(rpc("/auth/passkey/start-auth"));
        const auth = await this.waitFor(startAuthentication(serverOptions).catch(e => console.error(e)));
        if (!auth) {
            return false;
        }
        const form = document.querySelector("form.oe_login_form");
        form.querySelector("input[name='webauthn_response']").value = JSON.stringify(auth);
        form.querySelector("input[name='type']").value = "webauthn";
        form.submit();
    }
}

registry
    .category("public.interactions")
    .add("auth_passkey.passkey_login", PasskeyLogin);
