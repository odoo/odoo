import { patch } from "@web/core/utils/patch";
import { CheckIdentityForm } from "@web/core/session/check_identity";

patch(CheckIdentityForm.prototype, {
    async setup() {
        super.setup();
        this.authMethodTemplates = {
            ...this.authMethodTemplates,
            totp: {
                form: "auth_totp.CheckIdentityFormTOTP",
                linkString: "auth_totp.CheckIdentityLinkStringTOTP",
            },
        };
    },
});
