import { _t } from "@web/core/l10n/translation";
import { Plugin } from "../plugin";
import { closestBlock } from "../utils/blocks";
import { closestElement } from "../utils/dom_traversal";
import { isContentEditable, isTextNode } from "@html_editor/utils/dom_info";

export class TextDirectionPlugin extends Plugin {
    static name = "text_direction";
    static dependencies = ["selection", "split", "format"];
    resources = {
        powerboxItems: [
            {
                name: _t("Switch direction"),
                description: _t("Switch the text's direction"),
                category: "format",
                fontawesome: "fa-exchange",
                action(dispatch) {
                    dispatch("SWITCH_DIRECTION");
                },
            },
        ],
    };

    setup() {
        if (this.config.direction) {
            this.editable.setAttribute("dir", this.config.direction);
        }
        this.direction = this.config.direction || "ltr";
    }

    handleCommand(command) {
        switch (command) {
            case "SWITCH_DIRECTION":
                this.switchDirection();
                break;
        }
    }

    switchDirection() {
        const selection = this.shared.splitSelection();
        const selectedTextNodes = [selection.anchorNode, ...this.shared.getSelectedNodes()].filter(
            (n) => isTextNode(n) && isContentEditable(n) && n.nodeValue.trim().length
        );
        const blocks = new Set(
            selectedTextNodes.map(
                (textNode) => closestElement(textNode, "ul,ol") || closestBlock(textNode)
            )
        );

        const shouldApplyStyle = !this.shared.isSelectionFormat("switchDirection");

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
        this.dispatch("ADD_STEP");
    }
}
