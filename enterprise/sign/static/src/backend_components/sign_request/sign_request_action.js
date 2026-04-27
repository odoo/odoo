/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useRef, markup } from "@odoo/owl";
import { SignRequestControlPanel } from "@sign/backend_components/sign_request/sign_request_control_panel";
import { Document } from "@sign/components/sign_request/document_signable";
import { PDFIframe } from "@sign/components/sign_request/PDF_iframe";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

export class SignRequest extends Component {
    static template = "sign.SignRequest";
    static components = {
        SignRequestControlPanel,
        Document,
    };
    static props = { ...standardActionServiceProps };

    get markupHtml() {
        return markup(this.html);
    }

    get documentProps() {
        return {
            parent: this.documentRoot,
            PDFIframeClass: PDFIframe,
        };
    }

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        this.signInfo = useService("signInfo");
        const action = this.props.action;
        const context = action?.context;

        this.signInfo.reset({
            documentId: context.id || (action.params && action.params.id),
            signRequestToken: context.token || (action.params && action.params.token), // token could be sign.request.item's token if signabledocument
            createUid: context.create_uid || (action.params && action.params.create_uid),
            signRequestState: context.state || (action.params && action.params.state),
            requestItemStates: context.request_item_states,
            needToSign: context.need_to_sign || (action.params && action.params.need_to_sign),
            todayFormattedDate: context.today_formatted_date,
            name: action.name || action.params && action.params.name,
        });

        if (this.signInfo) {
            this.props.updateActionState({
                id: this.signInfo.get("documentId"),
                token: this.signInfo.get("signRequestToken"),
                create_uid: this.signInfo.get("createUid"),
                state: this.signInfo.get("signRequestState"),
                need_to_sign: this.signInfo.get("needToSign"),
                name: this.signInfo.get("name") || "",
            });
            this.env.config.setDisplayName(this.signInfo.get("name") || "");
        }

        this.documentRoot = useRef("sign-document");
        onWillStart(() => this.fetchDocument());
    }

    async fetchDocument() {
        if (!this.signInfo.get("documentId")) {
            return this.goBackToKanban();
        }
        const { html, context } = await rpc(
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
            goBackToKanban: this.goBackToKanban.bind(this),
        };
    }
}

registry.category("actions").add("sign.Document", SignRequest);
