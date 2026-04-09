import { _t } from "@web/core/l10n/translation";
import { Plugin } from "../plugin";
import { closestBlock } from "../utils/blocks";
import { closestElement } from "../utils/dom_traversal";
import { isContentEditable, isDirectionSwitched } from "@html_editor/utils/dom_info";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

export class TextDirectionPlugin extends Plugin {
    static id = "textDirection";
    static dependencies = ["selection", "history", "split"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "switchDirection",
                title: _t("Switch direction"),
                description: _t("Switch the text's direction"),
                icon: "fa-exchange",
                run: this.switchDirection.bind(this),
                isAvailable: isHtmlContentSupported,
            },
        ],
        powerbox_items: [
            {
                categoryId: "format",
                commandId: "switchDirection",
            },
        ],
    };

    setup() {
        if (this.config.direction && !this.editable.closest("[dir]")) {
            this.editable.setAttribute("dir", this.config.direction);
        }
        this.direction = this.config.direction || "ltr";
    }

    switchDirection() {
        const targetedNodes = this.dependencies.selection
            .getTargetedNodes()
            .filter(isContentEditable);
        const blocks = new Set(
            targetedNodes.map(
                (node) =>
                    closestElement(node, "ul,ol") ||
                    closestElement(node, "[data-embedded='toggleBlock']") ||
                    closestBlock(node)
            )
        );

        if (!blocks.size) {
            return;
        }

        const shouldApplyStyle = ![...blocks].every((block) =>
            isDirectionSwitched(block, this.editable)
        );

        for (const block of blocks) {
            for (const node of block.querySelectorAll("ul,ol")) {
                blocks.add(node);
            }
        }
        for (const block of blocks) {
            if (!shouldApplyStyle) {
                block.removeAttribute("dir");
            } else {
                block.setAttribute("dir", this.direction === "ltr" ? "rtl" : "ltr");
            }
        }

        for (const element of blocks) {
            const style = getComputedStyle(element);
            if (style.direction === "ltr" && style.textAlign === "right") {
                element.style.setProperty("text-align", "left");
            } else if (style.direction === "rtl" && style.textAlign === "left") {
                element.style.setProperty("text-align", "right");
            }
        }
        this.dependencies.history.addStep();
    }
}
