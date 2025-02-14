import { Plugin } from "@html_editor/plugin";
import { isEmptyBlock } from "@html_editor/utils/dom_info";
import { childNodes } from "@html_editor/utils/dom_traversal";
import { _t } from "@web/core/l10n/translation";
import { withSequence } from "@html_editor/utils/resource";

import { registry } from "@web/core/registry";
const commandRegistry = registry.category("discuss.channel_commands");

/**
 * @param {SelectionData} selectionData
 */
function target(selectionData, editable) {
    if (childNodes(editable).length !== 1) {
        return;
    }
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
    static dependencies = [
        "overlay",
        "selection",
        "delete",
        "history",
        "userCommand",
        "dom",
        "input",
    ];
    static shared = ["clear"];
    resources = {
        before_paste_handlers: this.onBeforePaste.bind(this),
        input_handlers: this.config.mailServices.onInput,
        hints: {
            text: this.composerComponent.placeholder,
            target,
        },
        user_commands: commandRegistry.getEntries().map(([name, command]) => ({
            id: command.methodName,
            title: name,
            description: command.help,
            icon: command.icon,
            isAvailable: (selection) => {
                const thread = this.composerComponent.props.composer.thread;
                if (thread?.model !== "discuss.channel") {
                    // channel commands are channel specific
                    return false;
                }
                const textContent = new DOMParser().parseFromString(
                    this.composerComponent.props.composer.text,
                    "text/html"
                ).documentElement.textContent;
                if (textContent !== "/") {
                    return false;
                }
                if (command.channel_types) {
                    return command.channel_types.includes(thread.channel_type);
                }
                return true;
            },
            run: async () => {
                this.dependencies.dom.insert("/" + name + "\u00A0");
                this.dependencies.history.addStep();
            },
        })),
        powerbox_categories: withSequence(1, {
            id: "channel_commands",
            name: _t("Channel Commands"),
        }),
        powerbox_items: commandRegistry.getEntries().map(([name, command]) => ({
            commandId: command.methodName,
            categoryId: "channel_commands",
        })),
    };

    setup() {
        this.addDomListener(this.editable, "keydown", this.config.mailServices.onKeydown);
        this.addDomListener(this.editable, "focusin", this.config.mailServices.onFocusin);
        this.addDomListener(this.editable, "focusout", this.config.mailServices.onFocusout);
    }

    get composerComponent() {
        return this.config.mailServices.composer;
    }

    /**
     * This doesn't work on firefox https://bugzilla.mozilla.org/show_bug.cgi?id=1699743
     */
    onBeforePaste(selection, ev) {
        if (!this.composerComponent.allowUpload) {
            return;
        }
        if (!ev.clipboardData?.items) {
            return;
        }
        const nonImgFiles = [...ev.clipboardData.items]
            .filter((item) => item.kind === "file" && !item.type.includes("image/"))
            .map((item) => item.getAsFile());
        if (nonImgFiles === 0) {
            return;
        }
        for (const file of nonImgFiles) {
            this.config.mailServices.attachmentUploader.uploadFile(file);
        }
    }

    clear() {
        this.editable.innerHTML = "<p><br/></p>";
        this.dependencies.selection.setCursorEnd(this.editable.lastChild);
        this.dependencies.history.addStep();
    }
}
