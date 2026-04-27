/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";
import { rpc } from "@web/core/network/rpc";
import { Component, useRef } from "@odoo/owl";

export class EncryptedDialog extends Component {
    static template = "sign.EncryptedDialog";
    static components = {
        Dialog,
    };
    static props = {
        close: Function,
    };

    setup() {
        this.passwordInput = useRef("password");
        this.dialog = useService("dialog");
        this.signInfo = useService("signInfo");
    }

    get dialogProps() {
        return {
            title: _t("PDF is encrypted"),
            fullscreen: this.env.isSmall,
            size: "md",
        };
    }

    async validatePassword() {
        const passwordInput = this.passwordInput.el;
        if (!passwordInput.value) {
            passwordInput.classList.toggle("is-invalid", !passwordInput.value);
            return false;
        }

        const route = `/sign/password/${this.signInfo.get("documentId")}`;
        const params = {
            password: passwordInput.value,
        };

        const response = await rpc(route, params);
        if (!response) {
            return this.dialog.add(AlertDialog, {
                body: _t("Password is incorrect."),
            });
        } else {
            this.props.close();
        }
    }
}
