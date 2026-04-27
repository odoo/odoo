/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { session } from "@web/session";
import { user } from "@web/core/user";
import { Dialog } from "@web/core/dialog/dialog";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { EncryptedDialog } from "./encrypted_dialog";
import { Component, onWillStart, useState } from "@odoo/owl";
import { isMobileOS } from "@web/core/browser/feature_detection";

export class ThankYouDialog extends Component {
    static template = "sign.ThankYouDialog";
    static components = {
        Dialog,
    };
    static props = {
        message: {
            type: String,
            optional: true,
        },
        subtitle: {
            type: String,
            optional: true,
        },
        redirectURL: {
            type: String,
            optional: true,
        },
        redirectURLText: {
            type: String,
            optional: true,
        },
        close: Function,
    };

    setup() {
        this.dialog = useService("dialog");
        this.signInfo = useService("signInfo");
        this.orm = useService("orm");
        this.state = useState({
            nextDocuments: [],
            buttons: [],
        });
        this.redirectURL = this.processURL(this.props.redirectURL);
        let defaultMessage = _t("You will get the signed document by email.");
        if (this.signInfo.get("companyCountryCode") === "US") {
            // U.S. signers may request a paper copy in addition to the electronic document,
            // as required by the ESIGN Act.
            defaultMessage = _t("You will get the signed document by email. You may also request a paper copy from the sender.");
        }
        this.message = this.props.message || defaultMessage;
        onWillStart(this.willStart);
        this.isMobileOS = isMobileOS();
    }

    get suggestSignUp() {
        return !user.userId;
    }

    get dialogProps() {
        return {
            size: "md",
        };
    }

    async checkIfEncryptedDialog() {
        const route = `/sign/encrypted/${this.signInfo.get("documentId")}`;
        return rpc(route);
    }

    async willStart() {
        const isEncrypted = await this.checkIfEncryptedDialog();
        if (isEncrypted) {
            this.dialog.add(EncryptedDialog);
        }
        this.signRequestState = await rpc(
            `/sign/sign_request_state/${this.signInfo.get("documentId")}/${this.signInfo.get(
                "signRequestToken"
            )}`
        );
        this.closeLabel = _t("Close");
        if (!session.is_frontend) {
            const result = await this.orm.call("sign.request", "get_close_values", [
                [this.signInfo.get("documentId")],
            ]);
            this.closeAction = result.action;
            this.closeLabel = result.label;
            const closeContext = result.custom_action ? { stackPosition: "replacePreviousAction" } : { clearBreadcrumbs: true };
            this.closeContext = closeContext;
        }
        if (!this.suggestSignUp && !session.is_website_user) {
            const result = await rpc("/sign/sign_request_items", {
                request_id: this.signInfo.get("documentId"),
                token: this.signInfo.get("signRequestToken"),
            });
            if (result && result.length) {
                this.state.nextDocuments = result.map((doc) => {
                    return {
                        id: doc.id,
                        name: doc.name,
                        date: doc.date,
                        user: doc.user || _t("Deleted User"),
                        accessToken: doc.token,
                        requestId: doc.requestId,
                        canceled: false,
                    };
                });
            }
        }

        this.generateButtons();
    }

    generateButtons() {
        if (this.redirectURL) {
            this.state.buttons.push({
                name: this.props.redirectURLText,
                click: () => {
                    window.location.assign(this.redirectURL);
                },
                classes: 'o_sign_thankyou_redirect_button',
            });
        }
        if (!this.redirectURL) {
            this.state.buttons.push({
                name: this.closeLabel,
                click: () => {
                    if (this.suggestSignUp) {
                        window.open(`https://odoo.com/app/sign`);
                    }
                    if (session.is_frontend) {
                        const signatureRequestId = this.signInfo.get("documentId");
                        window.location.assign(`/my/signature/${signatureRequestId}`);
                    } else {
                        this.props.close();
                        this.env.services.action.doAction(this.closeAction, this.closeContext);
                    }
                },
                classes: 'o_sign_thankyou_close_button'
            });
        }

        for (let i = 0; i < this.state.buttons.length; i++) {
            if (this.state.buttons[i].ignored) {
                continue;
            }
            const buttonClass = "btn btn-secondary";
            this.state.buttons[i].classes = `${this.state.buttons[i].classes} ${buttonClass}`;
        }
    }

    processURL(url) {
        if (url && !/^(f|ht)tps?:\/\//i.test(url)) {
            url = `http://${url}`;
        }
        return url;
    }

    goToDocument(id, token) {
        window.location.assign(this.makeURI("/sign/document", id, token, undefined, { portal: 1 }));
    }

    clickNextSign(id, token) {
        this.goToDocument(id, token);
    }

    clickButtonNext() {
        const nextDocument = this.state.nextDocuments.find((document) => !document.canceled);
        this.goToDocument(nextDocument.requestId, nextDocument.accessToken);
    }

    async clickNextCancel(doc) {
        await this.orm.call("sign.request", "cancel", [doc.requestId]);
        this.state.nextDocuments = this.state.nextDocuments.map((nextDoc) => {
            if (nextDoc.id === doc.id) {
                return {
                    ...nextDoc,
                    canceled: true,
                };
            }
            return nextDoc;
        });
        if (this.state.nextDocuments.every((doc) => doc.canceled)) {
            this.state.buttons = this.state.buttons.map((button) => {
                if (button.name === _t("Sign Next Document")) {
                    return {
                        ...button,
                        disabled: true,
                    };
                }
                return button;
            });
        }
    }

    async downloadDocument() {
        // Simply triggers a download of the document which the user just signed.
        window.location.assign(
            this.makeURI(
                "/sign/download",
                this.signInfo.get("documentId"),
                this.signInfo.get("signRequestToken"),
                "/completed"
            )
        );
    }

    makeURI(baseUrl, requestID, token, suffix = "", params = "") {
        // Helper function for constructing a URI.
        params = params ? "?" + new URLSearchParams(params).toString() : "";
        return `${baseUrl}/${requestID}/${token}${suffix}${params}`;
    }
}
