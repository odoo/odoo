import { Plugin } from "@html_editor/plugin";
import { getBaseContainerSelector } from "@html_editor/utils/base_container";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";

export class EmbeddedClipboardPlugin extends Plugin {
    static id = "embeddedClipboard";
    static dependencies = ["baseContainer", "history", "dom", "selection"];
    resources = {
        user_commands: [
            {
                id: "insertClipboard",
                title: _t("Clipboard"),
                description: _t("Add a clipboard section"),
                icon: "fa-pencil-square",
                run: this.insertClipboard.bind(this),
            },
        ],
        powerbox_items: [
            {
                categoryId: "media",
                commandId: "insertClipboard",
                isAvailable: (selection) =>
                    !closestElement(selection.anchorNode, "[data-embedded='clipboard']"),
            },
        ],
        mount_component_handlers: this.setupNewClipboard.bind(this),
    };

    insertClipboard() {
        const baseContainer = this.dependencies.baseContainer.createBaseContainer();
        const baseContainerNodeName = baseContainer.nodeName;
        const baseContainerClass = baseContainer.className;
        const baseContainerSelector = getBaseContainerSelector(baseContainerNodeName);
        const clipboardBlock = renderToElement("knowledge.EmbeddedClipboardBlueprint", {
            baseContainerNodeName,
            baseContainerAttributes: {
                class: baseContainerClass,
            },
        });
        this.dependencies.dom.insert(clipboardBlock);
        this.dependencies.selection.setCursorStart(
            clipboardBlock.querySelector(baseContainerSelector)
        );
        this.dependencies.history.addStep();
    }

    setupNewClipboard({ name, env }) {
        if (name === "clipboard") {
            Object.assign(env, {
                editorShared: {
                    preserveSelection: this.dependencies.selection.preserveSelection,
                },
            });
        }
    }
}
