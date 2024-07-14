/** @odoo-module **/

import { App, Component, xml, whenReady, useEffect, useComponent } from "@odoo/owl";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { useService } from "@web/core/utils/hooks";
import { templates } from "@web/core/assets";
import { makeEnv, startServices } from "@web/env";
import { SignRefusalDialog } from "@sign/dialogs/dialogs";
import { SignablePDFIframe } from "./signable_PDF_iframe";
import { buildPDFViewerURL } from "@sign/components/sign_request/utils";
import { _t } from "@web/core/l10n/translation";

function datasetFromElements(elements) {
    return Array.from(elements).map((el) => {
        return Object.entries(el.dataset).reduce((dataset, [key, value]) => {
            try {
                dataset[key] = JSON.parse(value);
            } catch {
                dataset[key] = value;
            }
            return dataset;
        }, {});
    });
}

export class Document extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.user = useService("user");
        this.ui = useService("ui");
        this.signInfo = useService("signInfo");
        useEffect(
            () => {
                this.getDataFromHTML();
                this.signInfo.set({
                    documentId: this.requestID,
                    signRequestToken: this.requestToken,
                    signRequestState: this.requestState,
                    signRequestItemToken: this.accessToken,
                });
            },
            () => []
        );
    }

    getDataFromHTML() {
        this.attachmentLocation = this.props.parent.querySelector(
            "#o_sign_input_attachment_location"
        )?.value;
        this.templateName = this.props.parent.querySelector("#o_sign_input_template_name")?.value;
        this.templateID = parseInt(
            this.props.parent.querySelector("#o_sign_input_template_id")?.value
        );
        this.templateItemsInProgress = parseInt(
            this.props.parent.querySelector("#o_sign_input_template_in_progress_count")?.value
        );
        this.requestID = parseInt(
            this.props.parent.querySelector("#o_sign_input_sign_request_id")?.value
        );
        this.requestToken = this.props.parent.querySelector(
            "#o_sign_input_sign_request_token"
        )?.value;
        this.requestState = this.props.parent.querySelector(
            "#o_sign_input_sign_request_state"
        )?.value;
        this.accessToken = this.props.parent.querySelector("#o_sign_input_access_token")?.value;
        this.templateEditable = Boolean(
            this.props.parent.querySelector("#o_sign_input_template_editable")
        );
        this.authMethod = this.props.parent.querySelector("#o_sign_input_auth_method")?.value;
        this.signerName = this.props.parent.querySelector("#o_sign_signer_name_input_info")?.value;
        this.signerPhone = this.props.parent.querySelector(
            "#o_sign_signer_phone_input_info"
        )?.value;
        this.redirectURL = this.props.parent.querySelector(
            "#o_sign_input_optional_redirect_url"
        )?.value;
        this.redirectURLText = this.props.parent.querySelector(
            "#o_sign_input_optional_redirect_url_text"
        )?.value;
        this.types = datasetFromElements(
            this.props.parent.querySelectorAll(".o_sign_field_type_input_info")
        );
        this.items = datasetFromElements(
            this.props.parent.querySelectorAll(".o_sign_item_input_info")
        );
        this.selectOptions = datasetFromElements(
            this.props.parent.querySelectorAll(".o_sign_select_options_input_info")
        );
        this.validateBanner = this.props.parent.querySelector(".o_sign_validate_banner");
        this.validateButton = this.props.parent.querySelector(".o_sign_validate_banner button");
        this.validateButtonText = this.validateButton?.textContent;
        this.currentRole = parseInt(
            this.props.parent.querySelector("#o_sign_input_current_role")?.value
        );
        this.currentName = this.props.parent.querySelector(
            "#o_sign_input_current_role_name"
        )?.value;
        this.isUnknownPublicUser = Boolean(
            this.props.parent.querySelector("#o_sign_is_public_user")
        );
        this.frameHash = this.props.parent.querySelector("#o_sign_input_sign_frame_hash")?.value;
        this.PDFIframe = this.props.parent.querySelector("iframe.o_sign_pdf_iframe");
        this.PDFIframe.setAttribute(
            "src",
            buildPDFViewerURL(this.attachmentLocation, this.env.isSmall)
        );
        this.PDFIframe.onload = () => {
            setTimeout(() => this.initializeIframe(), 1);
        };
    }

    initializeIframe() {
        this.iframe = new this.props.PDFIframeClass(
            this.PDFIframe.contentDocument,
            this.env,
            {
                rpc: this.rpc,
                orm: this.orm,
                dialog: this.dialog,
                user: this.user,
                ui: this.ui,
                signInfo: this.signInfo,
            },
            this.iframeProps
        );
    }

    get iframeProps() {
        return {
            attachmentLocation: this.attachmentLocation,
            requestID: this.requestID,
            requestToken: this.requestToken,
            accessToken: this.accessToken,
            signItemTypes: this.types,
            signItems: this.items,
            hasSignRequests: false,
            signItemOptions: this.selectOptions,
            currentRole: this.currentRole,
            currentName: this.currentName,
            readonly: this.PDFIframe.getAttribute("readonly") === "readonly",
            frameHash: this.frameHash,
            signerName: this.signerName,
            signerPhone: this.signerPhone,
            validateBanner: this.validateBanner,
            validateButton: this.validateButton,
            validateButtonText: this.validateButtonText,
            isUnknownPublicUser: this.isUnknownPublicUser,
            authMethod: this.authMethod,
            redirectURL: this.redirectURL,
            redirectURLText: this.redirectURLText,
            templateEditable: this.templateEditable,
        };
    }
}

Document.template = xml`<t t-slot='default'/>`;

function usePublicRefuseButton() {
    const component = useComponent();
    useEffect(
        () => {
            const refuseButton = document.querySelector(".o_sign_refuse_document_button");
            if (refuseButton) {
                refuseButton.addEventListener("click", () => {
                    component.dialog.add(SignRefusalDialog);
                });
            }
        },
        () => []
    );
}

export class SignableDocument extends Document {
    setup() {
        super.setup();
        this.coords = {};
        usePublicRefuseButton();
        useEffect(
            () => {
                if (this.requestID) {
                    // Geolocation
                    const askLocation = this.props.parent.getElementById(
                        "o_sign_ask_location_input"
                    );
                    if (askLocation && navigator.geolocation) {
                        navigator.geolocation.getCurrentPosition(
                            ({ coords: { latitude, longitude } }) => {
                                Object.assign(this.coords, {
                                    latitude,
                                    longitude,
                                });
                                if (this.requestState !== "shared") {
                                    this.rpc(
                                        `/sign/save_location/${this.requestID}/${this.accessToken}`,
                                        this.coords
                                    );
                                }
                            }
                        , () => {}, {enableHighAccuracy: true}
                        );
                    }
                }
            },
            () => [this.requestID]
        );
    }

    get iframeProps() {
        return {
            ...super.iframeProps,
            coords: this.coords,
        };
    }
}

SignableDocument.components = {
    MainComponentsContainer,
};
SignableDocument.template = xml`<MainComponentsContainer/>`;
/**
 * Mounts the SignableComponent
 * @param { HTMLElement } parent
 */
export async function initDocumentToSign(parent) {
    // Manually add 'sign' to module list and load the translations
    const env = makeEnv();
    await startServices(env);
    await whenReady();
    const app = new App(SignableDocument, {
        name: "Signable Document",
        env,
        props: { parent, PDFIframeClass: SignablePDFIframe },
        templates,
        dev: env.debug,
        translatableAttributes: ["data-tooltip"],
        translateFn: _t,
    });
    await app.mount(parent.body);
}
