/** @odoo-module **/

import { App, Component, xml, whenReady, useEffect, useComponent } from "@odoo/owl";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { useService } from "@web/core/utils/hooks";
import { getTemplate } from "@web/core/templates";
import { makeEnv, startServices } from "@web/env";
import { SignRefusalDialog } from "@sign/dialogs/dialogs";
import { SignablePDFIframe } from "./signable_PDF_iframe";
import { buildPDFViewerURL } from "@sign/components/sign_request/utils";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

export function datasetFromElements(elements) {
    return Array.from(elements).map((el) => {
        return Object.entries(el.dataset).reduce((dataset, [key, value]) => {
            try {
                const parsed = JSON.parse(value);
                if (key === "value" && typeof parsed === 'number' && parsed > Number.MAX_SAFE_INTEGER) {
                    // Keep numbers as strings below to avoid MAX_SAFE_INTEGER issues.
                    dataset[key] = value;
                } else {
                    dataset[key] = parsed;
                }
            } catch {
                dataset[key] = value;
            }
            return dataset;
        }, {});
    });
}

export class Document extends Component {
    static template = xml`<t t-slot='default'/>`;
    static props = ["parent", "PDFIframeClass"];

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
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
                    todayFormattedDate: this.todayFormattedDate,
                });
            },
            () => []
        );
    }

    getDataFromHTML() {
        const { el: parentEl } = this.props.parent;
        this.attachmentLocation = parentEl.querySelector(
            "#o_sign_input_attachment_location"
        )?.value;
        this.templateName = parentEl.querySelector("#o_sign_input_template_name")?.value;
        this.templateID = parseInt(parentEl.querySelector("#o_sign_input_template_id")?.value);
        this.templateItemsInProgress = parseInt(
            parentEl.querySelector("#o_sign_input_template_in_progress_count")?.value
        );
        this.requestID = parseInt(parentEl.querySelector("#o_sign_input_sign_request_id")?.value);
        this.requestToken = parentEl.querySelector("#o_sign_input_sign_request_token")?.value;
        this.requestState = parentEl.querySelector("#o_sign_input_sign_request_state")?.value;
        this.accessToken = parentEl.querySelector("#o_sign_input_access_token")?.value;
        this.todayFormattedDate = parentEl.querySelector("#o_sign_input_today_formatted_date")?.value;
        this.templateEditable = Boolean(parentEl.querySelector("#o_sign_input_template_editable"));
        this.authMethod = parentEl.querySelector("#o_sign_input_auth_method")?.value;
        this.signerName = parentEl.querySelector("#o_sign_signer_name_input_info")?.value;
        this.signerPhone = parentEl.querySelector("#o_sign_signer_phone_input_info")?.value;
        this.redirectURL = parentEl.querySelector("#o_sign_input_optional_redirect_url")?.value;
        this.redirectURLText = parentEl.querySelector(
            "#o_sign_input_optional_redirect_url"
        )?.value;
        this.redirectURLText = parentEl.querySelector(
            "#o_sign_input_optional_redirect_url_text"
        )?.value;
        this.types = datasetFromElements(
            parentEl.querySelectorAll(".o_sign_field_type_input_info")
        );
        this.items = datasetFromElements(parentEl.querySelectorAll(".o_sign_item_input_info"));
        this.selectOptions = datasetFromElements(
            parentEl.querySelectorAll(".o_sign_select_options_input_info")
        );
        this.validateBanner = parentEl.querySelector(".o_sign_validate_banner");
        this.validateButton = parentEl.querySelector(".o_validate_button");
        this.currentRole = parseInt(parentEl.querySelector("#o_sign_input_current_role")?.value);
        this.currentName = parentEl.querySelector("#o_sign_input_current_role_name")?.value;

        this.isUnknownPublicUser = Boolean(parentEl.querySelector("#o_sign_is_public_user"));
        this.frameHash = parentEl.querySelector("#o_sign_input_sign_frame_hash")?.value;
        this.PDFIframe = parentEl.querySelector("iframe.o_sign_pdf_iframe");
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
                rpc,
                orm: this.orm,
                dialog: this.dialog,
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
            isUnknownPublicUser: this.isUnknownPublicUser,
            authMethod: this.authMethod,
            redirectURL: this.redirectURL,
            redirectURLText: this.redirectURLText,
            templateEditable: this.templateEditable,
        };
    }
}

function usePublicRefuseButton() {
    const component = useComponent();
    useEffect(
        () => {
            const refuseButtons = document.querySelectorAll(".o_sign_refuse_document_button");
            if (refuseButtons) {
                refuseButtons.forEach((button) =>
                    button.addEventListener("click", () => {
                        component.dialog.add(SignRefusalDialog);
                    })
                );
            }
        },
        () => []
    );
}

export class SignableDocument extends Document {
    static components = {
        MainComponentsContainer,
    };
    static template = xml`<MainComponentsContainer/>`;

    setup() {
        super.setup();
        this.coords = {};
        usePublicRefuseButton();
        useEffect(
            () => {
                if (this.requestID) {
                    // Geolocation
                    const { el: parentEl } = this.props.parent;
                    const askLocation = parentEl.getElementById(
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
                                    rpc(
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
        props: {
            parent: {el: parent},
            PDFIframeClass: SignablePDFIframe },
        getTemplate,
        dev: env.debug,
        translatableAttributes: ["data-tooltip"],
        translateFn: _t,
    });
    await app.mount(parent.body);
}
