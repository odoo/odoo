/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { SignTemplateIframe } from "./sign_template_iframe";
import { SignTemplateTopBar } from "./sign_template_top_bar";
import { Component, useRef, useEffect, onWillUnmount } from "@odoo/owl";
import { buildPDFViewerURL } from "@sign/components/sign_request/utils";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class SignTemplateBody extends Component {
    static template = "sign.SignTemplateBody";
    static components = {
        SignTemplateTopBar,
    };
    static props = {
        signItemTypes: { type: Array },
        signItems: { type: Array },
        signRoles: { type: Array },
        hasSignRequests: { type: Boolean },
        signItemOptions: { type: Array },
        attachmentLocation: { type: String },
        signTemplate: { type: Object },
        goBackToKanban: { type: Function },
        manageTemplateAccess: { type: Boolean },
        isPDF: { type: Boolean },
    };

    setup() {
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.popover = useService("popover");
        this.dialog = useService("dialog");
        this.user = useService("user");
        this.PDFIframe = useRef("PDFIframe");
        this.PDFViewerURL = buildPDFViewerURL(this.props.attachmentLocation, this.env.isSmall);
        useEffect(
            () => {
                return this.waitForPDF();
            },
            () => []
        );
        onWillUnmount(() => {
            if (this.iframe) {
                this.saveTemplate();
                this.iframe.unmount();
                this.iframe = null;
            }
        });
    }

    waitForPDF() {
        this.PDFIframe.el.onload = () => setTimeout(() => this.doPDFPostLoad(), 1);
    }

    doPDFPostLoad() {
        this.preventDroppingImagesOnViewerContainer();
        this.iframe = new SignTemplateIframe(
            this.PDFIframe.el.contentDocument,
            this.env,
            {
                rpc: this.rpc,
                orm: this.orm,
                popover: this.popover,
                dialog: this.dialog,
                user: this.user,
            },
            {
                signItemTypes: this.props.signItemTypes,
                signItems: this.props.signItems,
                signRoles: this.props.signRoles,
                hasSignRequests: this.props.hasSignRequests,
                signItemOptions: this.props.signItemOptions,
                saveTemplate: () => this.saveTemplate(),
                rotatePDF: () => this.rotatePDF(),
            }
        );
    }

    /**
     * Prevents opening files in the pdf js viewer when dropping files/images to the viewerContainer
     * Ref: https://stackoverflow.com/a/68939139
     */
    preventDroppingImagesOnViewerContainer() {
        const viewerContainer = this.PDFIframe.el.contentDocument.querySelector("#viewerContainer");
        viewerContainer.addEventListener(
            "drop",
            (e) => {
                if (e.dataTransfer.files && e.dataTransfer.files.length) {
                    e.stopImmediatePropagation();
                    e.stopPropagation();
                }
            },
            true
        );
    }

    onTemplateNameChange(e) {
        const value = e.target.value;
        if (value != "") {
            this.props.signTemplate.display_name = value;
            this.saveTemplate(value);
        }
    }

    async saveTemplate(newTemplateName) {
        const [updatedSignItems, Id2UpdatedItem] = this.prepareTemplateData();
        const newId2ItemIdMap = await this.orm.call("sign.template", "update_from_pdfviewer", [
            this.props.signTemplate.id,
            updatedSignItems,
            this.iframe.deletedSignItemIds,
            newTemplateName || "",
        ]);

        if (!newId2ItemIdMap) {
            this.showBlockedTemplateDialog();
            return false;
        }

        for (const [newId, itemId] of Object.entries(newId2ItemIdMap)) {
            Id2UpdatedItem[newId].id = itemId;
        }
        this.notification.add(_t("Saved"), { type: "success" });
        return Id2UpdatedItem;
    }

    prepareTemplateData() {
        const updatedSignItems = {};
        const Id2UpdatedItem = {};
        const items = this.iframe?.signItems ?? {};
        for (const page in items) {
            for (const id in items[page]) {
                const signItem = items[page][id].data;
                if (signItem.updated) {
                    Id2UpdatedItem[id] = signItem;
                    const responsible = signItem.responsible;
                    updatedSignItems[id] = {
                        type_id: signItem.type_id[0],
                        required: signItem.required,
                        name: signItem.placeholder || signItem.name,
                        alignment: signItem.alignment,
                        option_ids: signItem.option_ids,
                        responsible_id: responsible,
                        page: page,
                        posX: signItem.posX,
                        posY: signItem.posY,
                        width: signItem.width,
                        height: signItem.height,
                    };

                    if (id < 0) {
                        updatedSignItems[id]["transaction_id"] = id;
                    }
                }
            }
        }
        return [updatedSignItems, Id2UpdatedItem];
    }

    async rotatePDF() {
        const result = await this.orm.call("sign.template", "rotate_pdf", [
            this.props.signTemplate.id,
        ]);
        if (!result) {
            this.showBlockedTemplateDialog();
        }

        return result;
    }

    showBlockedTemplateDialog() {
        this.dialog.add(AlertDialog, {
            confirm: () => {
                this.props.goBackToKanban();
            },
            body: _t("Somebody is already filling a document which uses this template"),
        });
    }
}
