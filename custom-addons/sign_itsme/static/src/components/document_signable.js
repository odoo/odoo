/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { SignablePDFIframe } from "@sign/components/sign_request/signable_PDF_iframe";
import { Document } from "@sign/components/sign_request/document_signable";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ItsmeDialog } from "@sign_itsme/dialogs/itsme_dialog";

patch(SignablePDFIframe.prototype, {
    postRender() {
        const res = super.postRender();
        if (this.props.errorMessage) {
            const [errorMessage, title] = processErrorMessage.call(this, this.props.errorMessage);
            this.dialog.add(
                AlertDialog,
                {
                    title: title || _t("Error"),
                    body: errorMessage,
                },
                {
                    onClose: () => {
                        deleteQueryParamFromURL("error_message");
                    },
                }
            );
        }
        if (this.props.showThankYouDialog) {
            this.openThankYouDialog();
        }
        return res;
    },

    async getAuthDialog() {
        if (this.props.authMethod === "itsme") {
            const credits = await this.rpc("/itsme/has_itsme_credits");
            if (credits) {
                const [route, params] = await this._getRouteAndParams();
                return {
                    component: ItsmeDialog,
                    props: {
                        route,
                        params,
                        onSuccess: () => {
                            this.openThankYouDialog();
                        },
                    },
                };
            }
        }
        return super.getAuthDialog();
    },
});

patch(Document.prototype, {
    getDataFromHTML() {
        super.getDataFromHTML();
        this.showThankYouDialog = Boolean(
            this.props.parent.querySelector("#o_sign_show_thank_you_dialog")
        );
        this.errorMessage = this.props.parent.querySelector("#o_sign_show_error_message")?.value;
    },

    get iframeProps() {
        const props = super.iframeProps;
        return {
            ...props,
            showThankYouDialog: this.showThankYouDialog,
            errorMessage: this.errorMessage,
        };
    },
});

function deleteQueryParamFromURL(param) {
    const url = new URL(location.href);
    url.searchParams.delete(param);
    window.history.replaceState(null, "", url);
}

/**
 * Processes special errors from the IAP server
 * @param { String } errorMessage
 * @returns { [String, Boolean] } error message, title or false
 */
function processErrorMessage(errorMessage) {
    const defaultTitle = false;
    const errorMap = {
        err_connection_odoo_instance: [
            _t(
                "The itsme® identification data could not be forwarded to Odoo, the signature could not be saved."
            ),
            defaultTitle,
        ],
        access_denied: [
            _t(
                "You have rejected the identification request or took too long to process it. You can try again to finalize your signature."
            ),
            _t("Identification refused"),
        ],
    };
    return errorMap[errorMessage] ? errorMap[errorMessage] : [errorMessage, defaultTitle];
}
