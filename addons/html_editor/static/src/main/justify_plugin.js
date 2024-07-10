import { Plugin } from "@html_editor/plugin";
import { closestBlock } from "@html_editor/utils/blocks";
import { isVisibleTextNode } from "@html_editor/utils/dom_info";
import { ToolbarItemSelector } from "./font/toolbar_item_selector";

const justifyItems = [
    {
        name: "Left",
        icon: "fa-align-left",
        commandId: "JUSTIFY_LEFT",
        cssProperty: "left",
    },
    {
        name: "Center",
        icon: "fa-align-center",
        commandId: "JUSTIFY_CENTER",
        cssProperty: "center",
    },
    {
        name: "Right",
        icon: "fa-align-right",
        commandId: "JUSTIFY_RIGHT",
        cssProperty: "right",
    },
    {
        name: "Justify",
        icon: "fa-align-justify",
        commandId: "JUSTIFY_FULL",
        cssProperty: "justify",
    },
];

export class JustifyPlugin extends Plugin {
    static name = "justify";
    static dependencies = ["selection"];
    /** @type { (p: JustifyPlugin) => Record<string, any> } */
    static resources = (p) => ({
        toolbarGroup: [
            {
                id: "align",
                sequence: 10,
                buttons: [
                    {
                        id: "align",
                        Component: ToolbarItemSelector,
                        props: {
                            getItems: () => justifyItems,
                            getEditableSelection: p.shared.getEditableSelection.bind(p),
                            onSelected: (item) => p.dispatch(item.commandId),
                            getItemFromSelection: (selection) => {
                                const block = closestBlock(selection.anchorNode);
                                const textAlign = getComputedStyle(block).textAlign;
                                return (
                                    justifyItems.find((item) => item.cssProperty === textAlign) ||
                                    justifyItems[0]
                                );
                            },
                        },
                    },
                ],
            },
        ],
    });

    handleCommand(command) {
        switch (command) {
            case "JUSTIFY_LEFT":
                this.align("left");
                break;
            case "JUSTIFY_RIGHT":
                this.align("right");
                break;
            case "JUSTIFY_CENTER":
                this.align("center");
                break;
            case "JUSTIFY_FULL":
                this.align("justify");
                break;
        }
    }

    align(mode) {
        const visitedBlocks = new Set();
        const traversedNode = this.shared.getTraversedNodes();
        for (const node of traversedNode) {
            if (isVisibleTextNode(node)) {
                const block = closestBlock(node);
                if (!visitedBlocks.has(block)) {
                    // todo @phoenix: check if it s correct in right to left ?
                    let textAlign = getComputedStyle(block).textAlign;
                    textAlign = textAlign === "start" ? "left" : textAlign;
                    if (textAlign !== mode && block.isContentEditable) {
                        block.style.textAlign = mode;
                    }
                    visitedBlocks.add(block);
                }
            }
        }
    }
}
