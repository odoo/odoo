/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useEffect, useRef, useState, markup } from "@odoo/owl";
import { SignRequestControlPanel } from "@sign/backend_components/sign_request/sign_request_control_panel";
import { Document } from "@sign/components/sign_request/document_signable";
import { PDFIframe } from "@sign/components/sign_request/PDF_iframe";

export class SignRequest extends Component {
    get markupHtml() {
        return markup(this.html);
    }

    get documentProps() {
        return {
            parent: this.documentRoot.el,
            PDFIframeClass: PDFIframe,
        };
    }

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.user = useService("user");
        this.action = useService("action");
        this.rpc = useService("rpc");
        this.signInfo = useService("signInfo");
        const action = this.props.action;
        const context = action?.context;

        this.signInfo.reset({
            documentId: context.id,
            signRequestToken: context.token, // token could be sign.request.item's token if signabledocument
            createUid: context.create_uid,
            signRequestState: context.state,
            requestItemStates: context.request_item_states,
            needToSign: context.need_to_sign,
        });

        this.documentRoot = useRef("sign-document");
        this.state = useState({
            refLoaded: false,
        });
        useEffect(
            () => {
                this.state.refLoaded = true;
            },
            () => []
        );

        onWillStart(() => this.fetchDocument());
    }

    async fetchDocument() {
        if (!this.signInfo.get("documentId")) {
            return this.goBackToKanban();
        }
        const { html, context } = await this.rpc(
            `/sign/get_document/${this.signInfo.get("documentId")}/${this.signInfo.get(
                "signRequestToken"
            )}`
        );
        this.html = html.trim();
        if (Object.keys(context).length > 0) {
            this.signInfo.set({
                refusalAllowed: context.refusal_allowed,
                signRequestItemToken: this.signInfo.get("signRequestToken"),
                signRequestToken: context.sign_request_token,
            });
        }

        const parser = new DOMParser();
        const doc = parser.parseFromString(this.html, "text/html");
        this.signerStatus = doc.querySelector(".o_sign_cp_pager");
    }

    goBackToKanban() {
        return this.action.doAction("sign.sign_request_action", { clearBreadcrumbs: true });
    }

    get controlPanelProps() {
        return {
            signerStatus: this.signerStatus,
        };
    }
}

SignRequest.template = "sign.SignRequest";
SignRequest.components = {
    SignRequestControlPanel,
    Document,
};

registry.category("actions").add("sign.Document", SignRequest);
