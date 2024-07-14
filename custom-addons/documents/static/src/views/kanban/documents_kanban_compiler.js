/** @odoo-module **/

import { KanbanCompiler } from "@web/views/kanban/kanban_compiler";
import { isTextNode } from "@web/views/view_compiler";
import { createElement } from "@web/core/utils/xml";

export class DocumentsKanbanCompiler extends KanbanCompiler {
    setup() {
        super.setup();
        this.compilers.push({ selector: "[t-name='kanban-box']", fn: this.compileCard });
        this.compilers.push({ selector: "div.o_documents_attachment", fn: this.compileDocumentsAttachment });
        this.compilers.push({ selector: "div.o_kanban_image_wrapper", fn: this.compileImageWrapper });
    }

    /**
     * Add some event handlers and prevent global click from messing with us.
     * @override
     */
    compileCard() {
        const result = super.compileGenericNode(...arguments);
        const cards = result.childNodes;
        for (const card of cards) {
            if (isTextNode(card)) {
                continue;
            }
            // Prevent default kanban renderer hotkey event from triggering
            const dummyElement = createElement("a");
            dummyElement.classList.add("o_hidden", "o_documents_dummy_action");
            card.prepend(dummyElement);
            card.setAttribute("t-on-dragstart.stop", `(ev) => __comp__.props.record.onDragStart(ev)`);
            const fileInput = card.querySelector("input.o_kanban_replace_document");
            if (fileInput) {
                fileInput.setAttribute("t-on-change.stop.prevent", `(ev) => __comp__.props.record.onReplaceDocument(ev)`);
                // Prevent double click issues
                fileInput.setAttribute("t-on-click.stop", `() => {}`);
            }
        }
        return result;
    }

    /**
     * Add some dynamic classes.
     */
    compileDocumentsAttachment() {
        const elem = super.compileGenericNode(...arguments);
        // `oe_file_request` if document is of type file request
        // `o_record_selected` if the document is currently selected
        elem.setAttribute(
            "t-attf-class",
            (elem.getAttribute("t-attf-class") || "") + " {{record.type.raw_value === 'empty' ? 'oe_file_request' : ''}} {{__comp__.props.record.selected ? 'o_record_selected' : ''}}"
        );
        // Selector and FileUploadProgressBar
        const content = new DOMParser().parseFromString(
            /*xml*/ `
            <t>
                <t t-set="fileUpload" t-value="__comp__.getFileUpload()"/>
                <i t-if="!fileUpload" class="fa fa-circle-thin o_record_selector" title="Select document"/>
                <t t-else="">
                    <FileUploadProgressBar fileUpload="fileUpload"/>
                </t>
            </t>
            `,
            "application/xml"
        );
        elem.prepend(...content.documentElement.children);
        return elem;
    }

    /**
     * Add some dynamic classes
     */
    compileImageWrapper() {
        const elem = super.compileGenericNode(...arguments);
        // `oe_kanban_previewer` if the file can be seen in the attachment viewer
        elem.setAttribute(
            "t-attf-class",
            (elem.getAttribute("t-attf-class") || "") + " {{(hasThumbnail or __comp__.props.record.isViewable() or youtubeVideoToken) ? 'oe_kanban_previewer' : ''}}"
        );
        return elem;
    }
}
