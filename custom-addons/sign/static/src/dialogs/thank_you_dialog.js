/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { session } from "@web/session";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { EncryptedDialog } from "./encrypted_dialog";
import { Component, onWillStart, useState } from "@odoo/owl";

export class ThankYouDialog extends Component {
    setup() {
        this.user = useService("user");
        this.rpc = useService("rpc");
        this.dialog = useService("dialog");
        this.signInfo = useService("signInfo");
        this.state = useState({
            nextDocuments: [],
            buttons: [],
        });
        this.redirectURL = this.processURL(this.props.redirectURL);
        this.message =
            this.props.message || _t("You will receive the final signed document by email.");
        onWillStart(this.willStart);
    }

    get suggestSignUp() {
        return session.user_id === false;
    }

    get dialogProps() {
        return {
            size: "md",
        };
    }

    async checkIfEncryptedDialog() {
        const route = `/sign/encrypted/${this.signInfo.get("documentId")}`;
        return this.rpc(route);
    }

    async willStart() {
        const isEncrypted = await this.checkIfEncryptedDialog();
        if (isEncrypted) {
            this.dialog.add(EncryptedDialog);
        }
        this.signRequestState = await this.rpc(
            `/sign/sign_request_state/${this.signInfo.get("documentId")}/${this.signInfo.get(
                "signRequestToken"
            )}`
        );
        if (!this.suggestSignUp && !session.is_website_user) {
            const result = await this.rpc("/sign/sign_request_items", {
                request_id: this.signInfo.get("documentId"),
                token: this.signInfo.get("signRequestToken"),
            });
            if (result && result.length) {
                this.state.nextDocuments = result.map((doc) => {
                    return {
                        id: doc.id,
                        name: doc.name,
                        date: doc.date,
                        user: doc.user,
                        accessToken: doc.token,
                        requestId: doc.requestId,
                        ignored: false,
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
            });
        }

        if (this.signRequestState === "signed") {
            this.state.buttons.push({
                name: _t("Download Document"),
                click: this.downloadDocument,
            });
        }

        if (this.suggestSignUp) {
            this.message += _t(" You can safely close this window.");
            this.state.buttons.push({
                name: _t("Sign Up for free"),
                classes: "btn btn-link ms-auto",
                ignored: true,
                click: () => {
                    window.open(
                        "https://www.odoo.com/trial?selected_app=sign&utm_source=db&utm_medium=sign",
                        "_blank"
                    );
                },
            });
        } else {
            this.state.buttons.push({
                name: _t("Close"),
                click: () => {
                    if (session.is_frontend) {
                        window.location.assign("/");
                    } else {
                        this.props.close();
                        this.env.services.action.doAction("sign.sign_template_action", {
                            clearBreadcrumbs: true,
                        });
                    }
                },
            });
            if (this.state.nextDocuments.length > 0) {
                this.state.buttons.push({
                    name: _t("Sign Next Document"),
                    classes: "o_thankyou_button_next",
                    click: this.clickButtonNext,
                });
            }
        }

        for (let i = 0; i < this.state.buttons.length; i++) {
            if (this.state.buttons[i].ignored) {
                continue;
            }
            const buttonClass = i === 0 ? "btn btn-primary" : "btn btn-secondary";
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
        const nextDocument = this.state.nextDocuments.find((document) => !document.ignored);
        this.goToDocument(nextDocument.requestId, nextDocument.accessToken);
    }

    async clickNextIgnore(doc) {
        const result = await this.rpc(
            `/sign/ignore_sign_request_item/${doc.id}/${doc.accessToken}`
        );
        if (result) {
            this.state.nextDocuments = this.state.nextDocuments.map((nextDoc) => {
                if (nextDoc.id === doc.id) {
                    return {
                        ...nextDoc,
                        ignored: true,
                    };
                }
                return nextDoc;
            });
            if (this.state.nextDocuments.every((doc) => doc.ignored)) {
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

ThankYouDialog.template = "sign.ThankYouDialog";
ThankYouDialog.components = {
    Dialog,
};
ThankYouDialog.props = {
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
