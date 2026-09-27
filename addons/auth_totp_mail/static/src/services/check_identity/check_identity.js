import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { CheckIdentityForm } from "@web/core/session/check_identity";

patch(CheckIdentityForm.prototype, {
    async setup() {
        super.setup();
        this.authMethodTemplates = {
            ...this.authMethodTemplates,
            totp_mail: {
                form: "auth_totp_mail.CheckIdentityFormTOTPMail",
                linkString: "auth_totp_mail.CheckIdentityLinkStringTOTPMail",
            },
        };
    },
    async onChangeAuthMethod(ev) {
        super.onChangeAuthMethod(ev);
        if (this.state.authMethod == "totp_mail") {
            try {
                await rpc("/auth-timeout/send-totp-mail-code");
            } catch (error) {
                if (error.data) {
                    this.state.error = error.data.message;
                } else {
                    this.state.error = "The code could not be sent by email";
                }
            }
        }
    },
});
