/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { AbstractBehavior } from "@knowledge/components/behaviors/abstract_behavior/abstract_behavior";
import { browser } from "@web/core/browser/browser";
import { SendAsMessageMacro, UseAsDescriptionMacro } from "@knowledge/macros/template_macros";
import { Tooltip } from "@web/core/tooltip/tooltip";
import { usePopover } from "@web/core/popover/popover_hook";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { setCursorStart } from "@web_editor/js/editor/odoo-editor/src/utils/utils";
import {
    useRef,
    markup,
} from "@odoo/owl";
import {
    BehaviorToolbar,
    BehaviorToolbarButton,
} from "@knowledge/components/behaviors/behavior_toolbar/behavior_toolbar";
import {
    getPropNameNode,
} from "@knowledge/js/knowledge_utils";


export class TemplateBehavior extends AbstractBehavior {
    static components = {
        BehaviorToolbar,
        BehaviorToolbarButton,
    };
    static props = {
        ...AbstractBehavior.props,
        content: { type: Object, optional: true },
    };
    static template = "knowledge.TemplateBehavior";

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.popover = usePopover(Tooltip);
        this.uiService = useService("ui");
        this.macrosServices = {
            action: this.actionService,
            dialog: this.dialogService,
            ui: this.uiService,
        };
        this.templateContent = useRef("templateContent");
        this.copyToClipboardButton = useChildRef();
        // <p><br/></p> can't be put in the template because adding a
        // t-if t-else in the template will add empty text nodes from
        // OWL in the editor, which are not compatible with collaborative:
        // if the template value is the props content, we get
        // text - value - text - text
        // and if the props content is undefined (else), we get
        // text - text - value - text
        // which means that for the same [value] nodes, we get different
        // html contents, which means they can't be synchronized.
        this.content = this.props.content || markup('<p><br/></p>');
        this.targetRecordInfo = this.knowledgeCommandsService.getCommandsRecordInfo();
        this.htmlFieldTargetMessage = _t('Use as %s', this.targetRecordInfo?.fieldInfo?.string || 'Description');
    }

    //--------------------------------------------------------------------------
    // TECHNICAL
    //--------------------------------------------------------------------------

    /**
     * Create a dataTransfer object with the editable content of the template
     * block, to be used for a paste event in the editor
     */
    _createHtmlDataTransfer() {
        const dataTransfer = new DataTransfer();
        const content = this.props.anchor.querySelector('.o_knowledge_content');
        dataTransfer.setData('text/odoo-editor', `<p></p>${content.innerHTML}<p></p>`);
        return dataTransfer;
    }

    //--------------------------------------------------------------------------
    // BUSINESS
    //--------------------------------------------------------------------------

    /**
     * Set the cursor of the user inside the template block when the user types
     * the `/clipboard` command (Used for a new TemplateBehavior on its first
     * mount).
     */
    setCursor() {
        setCursorStart(getPropNameNode("content", this.props.anchor).querySelector("p"));
    }

    //--------------------------------------------------------------------------
    // HANDLERS
    //--------------------------------------------------------------------------

    async onClickCopyToClipboard() {
        if (!this.templateContent.el) {
            return;
        }
        const selection = document.getSelection();
        selection.removeAllRanges();
        const range = new Range();
        range.selectNodeContents(this.templateContent.el);
        selection.addRange(range);
        if (document.execCommand("copy")) {
            // Nor the original `clipboard.write` function nor the polyfill
            // written in `clipboard.js` does trigger the `odooEditor` `copy`
            // handler, therefore `execCommand` should be called here so that
            // html content is properly handled within the editor.
            this.popover.open(this.copyToClipboardButton.el, {
                tooltip: _t("Content copied to clipboard."),
            });
            browser.setTimeout(this.popover.close, 800);
        }
        selection.removeAllRanges();
    }

    /**
     * Callback function called when the user clicks on the "Send as Message" button.
     * The function executes a macro that opens the latest form view, composes a
     * new message and attaches the associated file to it.
     * @param {Event} ev
     */
    onClickSendAsMessage(ev) {
        const dataTransfer = this._createHtmlDataTransfer();
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
        const dataTransfer = this._createHtmlDataTransfer();
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
