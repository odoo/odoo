/** @odoo-module **/

import { useBus } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { Document } from "@sign/components/sign_request/document_signable";
import { SignRequest } from "@sign/backend_components/sign_request/sign_request_action";
import { useSubEnv, EventBus } from "@odoo/owl";
import { SignableRequestControlPanel } from "@sign/backend_components/sign_request/signable_sign_request_control_panel";
import { EditWhileSigningSignablePDFIframe } from "@sign/backend_components/sign_request/edit_while_signing_signable_pdf_iframe";

class EditWhileSigningDocument extends Document {
    setup() {
        super.setup();
        useBus(this.env.editWhileSigningBus, "toggleEditBar", () => {
            this.iframe.toggleSidebar();
        });
    }
}

export class SignableSignRequest extends SignRequest {
    setup() {
        super.setup();
        this.signInfo.set({
            editWhileSigning: this.props.action.context.template_editable,
            tokenList: this.tokenList,
            nameList: this.nameList,
        });
        useSubEnv({
            editWhileSigningBus: new EventBus(),
        });
    }

    get nameList() {
        return this.props.action.context.name_list;
    }

    get tokenList() {
        return this.props.action.context.token_list;
    }

    get documentProps() {
        return {
            ...super.documentProps,
            PDFIframeClass: EditWhileSigningSignablePDFIframe,
        };
    }
}

SignableSignRequest.components = {
    ...SignableSignRequest.components,
    Document: EditWhileSigningDocument,
    SignRequestControlPanel: SignableRequestControlPanel,
};

registry.category("actions").add("sign.SignableDocument", SignableSignRequest);
