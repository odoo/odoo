/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, useState, useRef, useEffect } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { browser } from "@web/core/browser/browser";

export class SMSSignerDialog extends Component {
    static template = "sign.SMSSignerDialog";
    static components = {
        Dialog,
    };
    static props = {
        signerPhone: {
            type: String,
            optional: true,
        },
        postValidation: Function,
        close: Function,
    };

    setup() {
        this.validationCodeInput = useRef("code");
        this.phoneInput = useRef("phone");
        this.dialog = useService("dialog");
        this.signInfo = useService("signInfo");
        this.SMSInfo = { phoneNumber: this.props.signerPhone || "" };
        this.state = useState({
            sendingSMS: false,
            SMSCount: 0,
        });

        useEffect(
            () => {
                return () => {
                    browser.clearTimeout(this.timeout);
                };
            },
            () => []
        );
    }

    sendSMS(phoneNumber) {
        this.state.sendingSMS = true;
        const route = `/sign/send-sms/${this.signInfo.get("documentId")}/${this.signInfo.get(
            "signRequestItemToken"
        )}/${phoneNumber}`;
        rpc(route)
            .then((success) => {
                if (success) {
                    this.handleSendSMSSuccess();
                } else {
                    this.handleSMSError();
                }
            })
            .catch((_) => {
                this.handleSMSError();
            });
    }

    handleSendSMSSuccess() {
        this.timeout = browser.setTimeout(() => {
            this.state.sendingSMS = false;
            this.state.SMSCount++;
        }, 15000);
    }

    handleSMSError() {
        this.state.sendingSMS = false;
        this.dialog.add(AlertDialog, {
            title: _t("Error"),
            body: _t("Unable to send the SMS, please contact the sender of the document."),
        });
    }

    onSendSMSClick(e) {
        const sendButton = e.target;
        sendButton.setAttribute("disabled", true);
        const phoneNumber = this.phoneInput.el.value;
        if (phoneNumber) {
            this.SMSInfo.phoneNumber = phoneNumber;
            this.sendSMS(phoneNumber);
        }
        sendButton.removeAttribute("disabled");
    }

    async validateSMS(e) {
        const validateButton = e.target;
        const validationCode = this.validationCodeInput.el?.value;
        if (!validationCode) {
            this.validationCodeInput.el.classList.toggle("is-invalid");
            return false;
        }
        validateButton.setAttribute("disabled", true);
        await this.props.postValidation(validationCode);
        validateButton.removeAttribute("disabled");
        this.props.close();
    }

    get dialogProps() {
        return {
            size: "md",
            title: _t("Final Validation"),
            fullscreen: this.env.isSmall,
        };
    }
}
