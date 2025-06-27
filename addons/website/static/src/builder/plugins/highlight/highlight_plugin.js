import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { Component, xml, useRef, reactive, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { registry } from "@web/core/registry";
import { HighlightConfigurator } from "./highlight_configurator";
import { StackingComponent, useStackingComponentState } from "./stacking_component";
import { formatsSpecs } from "@html_editor/utils/formatting";
import { closestElement, descendants } from "@html_editor/utils/dom_traversal";
import { removeClass, removeStyle } from "@html_editor/utils/dom";
import { isTextNode } from "@html_editor/utils/dom_info";
import { getCurrentTextHighlight } from "@website/js/highlight_utils";
import { isCSSColor, rgbaToHex } from "@web/core/utils/colors";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { nodeSize } from "@html_editor/utils/position";

export class HighlightPlugin extends Plugin {
    static id = "highlight";
    static dependencies = ["history", "selection", "split", "format"];
    resources = {
        toolbar_groups: [withSequence(50, { id: "websiteDecoration" })],
        toolbar_items: [
            {
                id: "highlight",
                groupId: "websiteDecoration",
                description: _t("Apply highlight"),
                Component: HighlightToolbarButton,
                props: {
                    highlightConfiguratorProps: {
                        applyHighlight: this.applyHighlight.bind(this),
                        previewHighlight: this.previewHighlight.bind(this),
                        revertHighlight: this.revertHighlight.bind(this),
                        applyHighlightStyle: this.applyHighlightStyle.bind(this),
                        previewHighlightStyle: this.previewHighlightStyle.bind(this),
                        revertHighlightStyle: this.revertHighlightStyle.bind(this),
                        getHighlightState: () => this.highlightState,
                        getUsedCustomColors: this.getUsedCustomColors.bind(this),
                        deleteHighlight: this.deleteSelectedHighlight.bind(this),
                    },
                    onClick: this.completeHighlightSelection.bind(this),
                },
                isAvailable: isHtmlContentSupported,
            },
        ],
        clean_for_save_handlers: ({ root }) => {
            for (const svg of root.querySelectorAll(".o_text_highlight_svg")) {
                svg.remove();
            }
        },
        /**
         * @param {MutationRecord} mutationRecord
         */
        savable_mutation_record_predicates: (mutationRecord) =>
            ![...mutationRecord.addedNodes, ...mutationRecord.removedNodes].some((node) =>
                closestElement(node, ".o_text_highlight_svg")
            ),
        normalize_handlers: (root) => {
            // Remove highlight SVGs when the text is removed.
            for (const svg of root.querySelectorAll(".o_text_highlight_svg")) {
                if (!svg.closest(".o_text_highlight")) {
                    svg.remove();
                }
            }
        },
        format_splittable_class: (className) => className.startsWith("o_text_highlight"),
        selectionchange_handlers: this.updateSelectedHighlight.bind(this),
        collapsed_selection_toolbar_predicate: (selectionData) =>
            !!closestElement(selectionData.editableSelection.anchorNode, ".o_text_highlight"),
        remove_format_handlers: () => {
            const highlightedNodes = this.getSelectedHighlightNodes();
            for (const node of new Set(highlightedNodes)) {
                for (const svg of node.querySelectorAll(".o_text_highlight_svg")) {
                    svg.remove();
                }
            }
        },
    };

    setup() {
        this.previewableApplyHighlight = this.dependencies.history.makePreviewableOperation(
            this._applyHighlight.bind(this)
        );
        this.previewableApplyHighlightStyle = this.dependencies.history.makePreviewableOperation(
            this._applyHighlightStyle.bind(this)
        );
        this.highlightState = reactive({
            highlightId: undefined,
            color: "",
            thickness: undefined,
        });
    }

    updateSelectedHighlight() {
        const nodes = this.getSelectedHighlightNodes();
        const uniqueNodes = new Set(nodes);
        if (uniqueNodes.size === 0) {
            this.highlightState.highlightId = undefined;
            this.highlightState.color = "";
            this.highlightState.thickness = undefined;
            return;
        }

        this.highlightState.highlightId =
            uniqueNodes.size > 1 ? "multiple" : getCurrentTextHighlight(nodes[0]);
        if (this.highlightState.highlightId) {
            // If multiple highlights are selected, either show the common highlight properties
            // or nothing if none
            const style = nodes.map((node) =>
                getComputedStyle(node).getPropertyValue("--text-highlight-color")
            );
            this.highlightState.color = style.every((v) => v === style[0]) ? style[0] : undefined;
            const thickness = nodes.map((node) =>
                getComputedStyle(node).getPropertyValue("--text-highlight-width")
            );
            this.highlightState.thickness = thickness.every((v) => v === thickness[0])
                ? parseInt(thickness[0])
                : "";
        }
    }

    _applyHighlight(highlightId) {
        const highlightedNodes = this.getSelectedHighlightNodes();
        for (const node of new Set(highlightedNodes)) {
            for (const svg of node.querySelectorAll(".o_text_highlight_svg")) {
                svg.remove();
            }
        }

        let thicknessToRestore;
        let colorToRestore;
        if (highlightedNodes.length > 0) {
            const style = getComputedStyle(highlightedNodes[0]);
            colorToRestore = style.getPropertyValue("--text-highlight-color");
            thicknessToRestore = style.getPropertyValue("--text-highlight-width");
        }

        this.dependencies.format.formatSelection("highlight", {
            formatProps: { highlightId, colorToRestore, thicknessToRestore },
            applyStyle: true,
        });

        this.updateSelectedHighlight();
    }

    applyHighlight(highlightId) {
        this.previewableApplyHighlight.commit(highlightId);
    }
    previewHighlight(highlightId) {
        this.previewableApplyHighlight.preview(highlightId);
    }
    revertHighlight() {
        this.previewableApplyHighlight.revert();
    }

    _applyHighlightStyle(style, value) {
        const highlightedNodes = this.getSelectedHighlightNodes();
        for (const node of new Set(highlightedNodes)) {
            node.style.setProperty(style, value);
        }
        this.updateSelectedHighlight();
    }

    applyHighlightStyle(style, value) {
        this.previewableApplyHighlightStyle.commit(style, value);
    }
    previewHighlightStyle(style, value) {
        this.previewableApplyHighlightStyle.preview(style, value);
    }
    revertHighlightStyle() {
        this.previewableApplyHighlightStyle.revert();
    }
    getUsedCustomColors() {
        const highlights = this.editable.querySelectorAll(".o_text_highlight");
        const usedCustomColors = new Set();
        for (const highlight of highlights) {
            const style = getComputedStyle(highlight);
            const color = style.getPropertyValue("--text-highlight-color");
            if (isCSSColor(color)) {
                usedCustomColors.add(rgbaToHex(color).toLowerCase());
            }
        }
        return usedCustomColors;
    }

    getSelectedHighlightNodes() {
        return this.dependencies.selection
            .getTargetedNodes()
            .map((n) => closestElement(n, ".o_text_highlight"))
            .filter(Boolean);
    }
    /**
     * This method completes the selection by ensuring that the selection
     * always cover all the text nodes within the highlighted elements.
     */
    completeHighlightSelection() {
        const targetedNodes = this.dependencies.selection
            .getTargetedNodes()
            .map(
                (n) =>
                    closestElement(n, ".o_text_highlight") ||
                    n?.querySelector?.(".o_text_highlight")
            );
        let { startContainer, startOffset, endContainer, endOffset, direction } =
            this.dependencies.selection.getEditableSelection();

        if (targetedNodes.length > 0) {
            if (targetedNodes[0]?.matches?.(".o_text_highlight")) {
                const firstTextNode = descendants(targetedNodes[0]).filter(isTextNode)[0];
                startContainer = firstTextNode;
                startOffset = 0;
            }
            if (targetedNodes.at(-1)?.matches?.(".o_text_highlight")) {
                const lastTextNode = descendants(targetedNodes.at(-1)).filter(isTextNode).at(-1);
                endContainer = lastTextNode;
                endOffset = nodeSize(endContainer);
            }
        }
        const [anchorNode, anchorOffset, focusNode, focusOffset] = direction
            ? [startContainer, startOffset, endContainer, endOffset]
            : [endContainer, endOffset, startContainer, startOffset];
        this.dependencies.selection.setSelection({
            anchorNode,
            anchorOffset,
            focusNode,
            focusOffset,
        });
        this.dependencies.selection.focusEditable();
        this.dependencies.history.stageSelection();
    }

    deleteSelectedHighlight() {
        const highlightedNodes = this.getSelectedHighlightNodes();
        for (const node of new Set(highlightedNodes)) {
            for (const svg of node.querySelectorAll(".o_text_highlight_svg")) {
                svg.remove();
            }
        }

        this.dependencies.format.formatSelection("highlight", {
            applyStyle: false,
        });
        this.updateSelectedHighlight();
    }
}
registry.category("website-plugins").add(HighlightPlugin.id, HighlightPlugin);

// Todo: formatsSpecs should allow to be register new formats through resources.
formatsSpecs.highlight = {
    isFormatted: (node) => closestElement(node)?.classList.contains("o_text_highlight"),
    hasStyle: (node) => closestElement(node)?.classList.contains("o_text_highlight"),
    addStyle: (node, { highlightId, thicknessToRestore, colorToRestore }) => {
        node.dispatchEvent(new Event("text_highlight_added", { bubbles: true }));
        node.classList.add("o_text_highlight", `o_text_highlight_${highlightId}`);
        if (colorToRestore && colorToRestore !== "currentColor") {
            node.style.setProperty("--text-highlight-color", colorToRestore);
        }
        if (thicknessToRestore) {
            node.style.setProperty("--text-highlight-width", thicknessToRestore);
        } else {
            const style = getComputedStyle(node);
            node.style.setProperty(
                "--text-highlight-width",
                Math.round(parseFloat(style.fontSize) * 0.1) + "px"
            );
        }
    },
    removeStyle: (node) => {
        removeClass(
            node,
            ...[...node.classList].filter((cls) => cls.startsWith("o_text_highlight"))
        );
        removeStyle(node, "--text-highlight-width");
        removeStyle(node, "--text-highlight-color");
    },
};

class HighlightToolbarButton extends Component {
    static props = {
        highlightConfiguratorProps: Object,
        onClick: Function,
        title: String,
        getSelection: Function,
    };
    static template = xml`
        <button t-ref="root" t-attf-class="btn btn-light o-select-highlight" t-on-click="openHighlightConfigurator" t-att-title="props.title">
            <i class="fa oi oi-text-effect oi-fw py-1"/>
        </button>
    `;

    setup() {
        this.highlightState = useState(this.props.highlightConfiguratorProps.getHighlightState());
        this.root = useRef("root");
        this.componentStack = useStackingComponentState();
        this.componentStack.push(HighlightConfigurator, {
            componentStack: this.componentStack,
            ...this.props.highlightConfiguratorProps,
        });
        this.configuratorPopover = usePopover(StackingComponent, {
            onClose: () => {
                while (this.componentStack.stack.length > 1) {
                    this.componentStack.pop();
                }
            },
        });
    }
    openHighlightConfigurator() {
        this.props.onClick();
        this.configuratorPopover.open(this.root.el, {
            stackState: this.componentStack,
            style: "max-height: 300px; width: 262px",
            class: "d-flex flex-column p-2",
        });
    }
}
