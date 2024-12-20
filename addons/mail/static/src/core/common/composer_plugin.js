import { Plugin } from "@html_editor/plugin";
import {
    Component,
    markup,
    onMounted,
    useChildSubEnv,
    useEffect,
    useRef,
    useState,
    useExternalListener,
    toRaw,
} from "@odoo/owl";
import { isEmptyBlock } from "@html_editor/utils/dom_info";
import { _t } from "@web/core/l10n/translation";

/**
 * @param {SelectionData} selectionData
 */
function target(selectionData) {
    const node = selectionData.editableSelection.anchorNode;
    const el = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
    if (
        selectionData.documentSelectionIsInEditable &&
        (el.tagName === "DIV" || el.tagName === "P") &&
        isEmptyBlock(el)
    ) {
        return el;
    }
}

export class ComposerPlugin extends Plugin {
    static id = "composer";
    static dependencies = ["overlay", "selection", "history", "userCommand", "dom"];
    static shared = [];
    resources = {
        before_split_block_handlers: this.onBeforeSplitBlock.bind(this),
        before_paste_handlers: this.onBeforePaste.bind(this),
        hints: {
            text: this.config.placeholder,
            target,
        },
    };
    setup() {
        // this.addDomListener(this.editable, "keydown", this.onKeyDown);
    }

    onBeforeSplitBlock(e) {
        debugger
        const composer = toRaw(this.config.mailServices.composer);
        if (composer.message) {
            this.config.mailServices.editMessage();
        } else {
            this.config.mailServices.sendMessage();
        }
    }

    /**
     * This doesn't work on firefox https://bugzilla.mozilla.org/show_bug.cgi?id=1699743
     */
    onBeforePaste(selection, ev) {
        // if (!this.allowUpload) {
        //     return;
        // }
        if (!ev.clipboardData?.items) {
            return;
        }
        const nonImgFiles = [...ev.clipboardData.items]
            .filter((item) => item.kind === "file" && !item.type.includes("image/"))
            .map((item) => item.getAsFile());
        if (nonImgFiles === 0) {
            return;
        }
        // ev.preventDefault();
        for (const file of nonImgFiles) {
            this.config.mailServices.attachmentUploader.uploadFile(file);
        }
    }
}
