/** @odoo-module **/

import { Component, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";

export class PublicSignerDialog extends Component {
    static template = "sign.PublicSignerDialog";
    static components = {
        Dialog,
    };
    static props = {
        name: String,
        mail: String,
        postValidation: Function,
        close: Function,
    };

    setup() {
        this.nameInput = useRef("name");
        this.mailInput = useRef("mail");
        this.signInfo = useService("signInfo");
    }

    get dialogProps() {
        return {
            title: _t("Final Validation"),
            size: "md",
            technical: this.env.isSmall,
            fullscreen: this.env.isSmall,
        };
    }

    async submit() {
        const name = this.nameInput.el.value;
        const mail = this.mailInput.el.value;
        if (!this.validateForm(name, mail)) {
            return false;
        }

        const response = await rpc(
            `/sign/send_public/${this.signInfo.get("documentId")}/${this.signInfo.get(
                "signRequestToken"
            )}`,
            { name, mail }
        );

        await this.props.postValidation(
            response["requestID"],
            response["requestToken"],
            response["accessToken"]
        );
        this.props.close();
    }

    validateForm(name, mail) {
        const isEmailInvalid = !mail || mail.indexOf("@") < 0;
        if (!name || isEmailInvalid) {
            this.nameInput.el.classList.toggle("is-invalid", !name);
            this.mailInput.el.classList.toggle("is-invalid", isEmailInvalid);
            return false;
        }
        return true;
    }
}
