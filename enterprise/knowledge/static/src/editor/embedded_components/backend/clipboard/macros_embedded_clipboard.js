import { SIGNATURE_CLASS } from "@html_editor/main/signature_plugin";
import {
    getEditableDescendants,
    getEmbeddedProps,
} from "@html_editor/others/embedded_component_utils";
import { isEmptyBlock } from "@html_editor/utils/dom_info";
import { _t } from "@web/core/l10n/translation";
import { EmbeddedClipboardComponent } from "@knowledge/editor/embedded_components/core/clipboard/embedded_clipboard";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { renderToElement } from "@web/core/utils/render";
import { SendAsMessageMacro, UseAsDescriptionMacro } from "@knowledge/macros/clipboard_macros";
import { markup } from "@odoo/owl";

export class MacrosEmbeddedClipboardComponent extends EmbeddedClipboardComponent {
    static template = "knowledge.MacrosEmbeddedClipboard";

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.knowledgeCommandsService = useService("knowledgeCommandsService");
        this.orm = useService("orm");
        this.uiService = useService("ui");
        this.macrosServices = {
            action: this.actionService,
            dialog: this.dialogService,
            ui: this.uiService,
        };
        this.targetRecordInfo = this.knowledgeCommandsService.getCommandsRecordInfo();
        this.htmlFieldTargetMessage = _t(
            "Use as %s",
            this.targetRecordInfo?.fieldInfo?.string || "Description"
        );
    }

    //--------------------------------------------------------------------------
    // TECHNICAL
    //--------------------------------------------------------------------------

    /**
     * Create a dataTransfer object with the editable content of the template
     * block, to be used for a paste event in the editor
     */
    createHtmlDataTransfer() {
        const dataTransfer = new DataTransfer();
        const content = this.descendants.clipboardContent;
        const value = `<p></p>${content.innerHTML}<p></p>`;
        dataTransfer.setData("application/vnd.odoo.odoo-editor", value);
        return dataTransfer;
    }

    //--------------------------------------------------------------------------
    // HANDLERS
    //--------------------------------------------------------------------------

    /**
     * Callback function called when the user clicks on the "Send as Message" button.
     * The function executes a macro that opens the latest form view, composes a
     * new message and attaches the associated file to it.
     * @param {Event} ev
     */
    async onClickSendAsMessage(ev) {
        const rows = await this.orm.read("res.users", [user.userId], ["signature"]);
        const signature = renderToElement("html_editor.Signature", {
            signature: markup(rows[0]?.signature || ""),
            signatureClass: SIGNATURE_CLASS,
        });

        const dataTransfer = new DataTransfer();
        dataTransfer.setData("application/vnd.odoo.odoo-editor",
            this.descendants.clipboardContent.innerHTML + (
                isEmptyBlock(signature) ? "" : signature.outerHTML));

        const macro = new SendAsMessageMacro({
            targetXmlDoc: this.targetRecordInfo.xmlDoc,
            breadcrumbs: this.targetRecordInfo.breadcrumbs,
            data: {
                dataTransfer: dataTransfer,
            },
            services: this.macrosServices,
        });
        macro.start();
    }

    /**
     * Callback function called when the user clicks on the "Use As ..." button.
     * The function executes a macro that opens the latest form view containing
     * a valid target field (see `KNOWLEDGE_RECORDED_FIELD_NAMES`) and copy/past
     * the content of the template to it.
     * @param {Event} ev
     */
    onClickUseAsDescription(ev) {
        const dataTransfer = this.createHtmlDataTransfer();
        const macro = new UseAsDescriptionMacro({
            targetXmlDoc: this.targetRecordInfo.xmlDoc,
            breadcrumbs: this.targetRecordInfo.breadcrumbs,
            data: {
                fieldName: this.targetRecordInfo.fieldInfo.name,
                pageName: this.targetRecordInfo.fieldInfo.pageName,
                dataTransfer: dataTransfer,
            },
            services: this.macrosServices,
        });
        macro.start();
    }
}

export const macrosClipboardEmbedding = {
    name: "clipboard",
    Component: MacrosEmbeddedClipboardComponent,
    getProps: (host) => {
        return { host, ...getEmbeddedProps(host) };
    },
    getEditableDescendants: getEditableDescendants,
};
