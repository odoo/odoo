/** @odoo-module native */
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import { Plugin } from "@html_editor/plugin";
import { removeClass, removeStyle } from "@html_editor/utils/dom";
import { isTextNode } from "@html_editor/utils/dom_info";
import { closestElement, descendants } from "@html_editor/utils/dom_traversal";
import { formatsSpecs } from "@html_editor/utils/formatting";
import { nodeSize } from "@html_editor/utils/position";
import { withSequence } from "@html_editor/utils/resource";
import { Component, reactive, useRef, useState, xml } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { isCSSColor, rgbaToHex } from "@web/core/utils/format/colors";
import { usePopover } from "@web/ui/popover";
import { getCurrentTextHighlight } from "@website/js/highlight_utils";

import { HighlightConfigurator } from "./highlight_configurator.js";
import { StackingComponent, useStackingComponentState } from "./stacking_component.js";

const log = makeLogger("website.builder.plugin.highlight");

export class HighlightPlugin extends Plugin {
    static id = "highlight";
    static dependencies = [
        "history",
        "selection",
        "split",
        "format",
        "edit_interaction",
    ];
    /** @type {import("plugins").WebsiteResources} */
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
                        getMaxFontSize: this.getMaxFontSize.bind(this),
                    },
                    onClick: this.completeHighlightSelection.bind(this),
                },
                isAvailable: isHtmlContentSupported,
            },
        ],
        toolbar_namespace_providers: [
            withSequence(
                90,
                (targetedNodes, editableSelection) =>
                    closestElement(editableSelection.anchorNode, ".o_text_highlight") &&
                    "compact",
            ),
        ],
        normalize_handlers: (root) => {
            const endNormalize = log.perf("normalize text_highlight_added dispatch");
            for (const node of root.querySelectorAll(".o_text_highlight")) {
                node.dispatchEvent(
                    new Event("text_highlight_added", { bubbles: true }),
                );
            }
            endNormalize(() => ({
                count: root.querySelectorAll(".o_text_highlight").length,
            }));
        },
        format_class_predicates: (className) =>
            className.startsWith("o_text_highlight"),
        selectionchange_handlers: this.updateSelectedHighlight.bind(this),
        remove_all_formats_handlers: () => {
            log.logic("stop text_highlight interaction: remove all formats");
            this.dependencies.edit_interaction.stopInteraction(
                "website.text_highlight",
            );
        },
        format_selection_handlers: () => {
            log.logic("stop text_highlight interaction: format selection");
            this.dependencies.edit_interaction.stopInteraction(
                "website.text_highlight",
            );
        },
        before_save_handlers: () => {
            log.logic("stop text_highlight interaction: before save");
            this.dependencies.edit_interaction.stopInteraction(
                "website.text_highlight",
            );
        },
    };

    setup() {
        log.lifecycle("setup");
        this.previewableApplyHighlight =
            this.dependencies.history.makePreviewableOperation(
                this._applyHighlight.bind(this),
            );
        this.previewableApplyHighlightStyle =
            this.dependencies.history.makePreviewableOperation(
                this._applyHighlightStyle.bind(this),
            );
        this.highlightState = reactive({
            highlightId: undefined,
            color: "",
            thickness: undefined,
        });
    }

    getMaxFontSize() {
        const nodes = this.dependencies.selection
            .getTargetedNodes()
            .map((n) => closestElement(n, "*"))
            .filter(Boolean);
        const uniqueNodes = new Set(nodes);
        if (uniqueNodes.size === 0) {
            uniqueNodes.add(this.document.body);
        }
        let max = 0;
        for (const node of uniqueNodes) {
            const size = parseFloat(getComputedStyle(node).fontSize);
            if (size > max) {
                max = size;
            }
        }
        return max;
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
            log.logic("updateSelectedHighlight: highlight in selection", () => ({
                highlightId: this.highlightState.highlightId,
                nodes: nodes.length,
                unique: uniqueNodes.size,
            }));
            const style = nodes.map((node) =>
                getComputedStyle(node).getPropertyValue("--text-highlight-color"),
            );
            this.highlightState.color = style.every((v) => v === style[0])
                ? style[0]
                : getComputedStyle(this.document.body).getPropertyValue(
                      "--hb-cp-o-color-1",
                  );
            const thickness = nodes.map((node) =>
                getComputedStyle(node).getPropertyValue("--text-highlight-width"),
            );
            this.highlightState.thickness = thickness.every((v) => v === thickness[0])
                ? parseInt(thickness[0])
                : 2;
        }
    }

    _applyHighlight(highlightId) {
        const highlightedNodes = this.getSelectedHighlightNodes();
        let thicknessToRestore = "2px";
        let colorToRestore = "var(--o-color-1)";
        if (highlightedNodes.length > 0) {
            const style = getComputedStyle(highlightedNodes[0]);
            colorToRestore = style.getPropertyValue("--text-highlight-color");
            thicknessToRestore = style.getPropertyValue("--text-highlight-width");
        }
        log.logic("_applyHighlight", () => ({
            highlightId,
            replacing: highlightedNodes.length,
            colorToRestore,
            thicknessToRestore,
        }));

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
        log.pipeline("_applyHighlightStyle", () => ({
            style,
            value,
            nodes: new Set(highlightedNodes).size,
        }));
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
        const endScan = log.perf("getUsedCustomColors");
        const highlights = this.editable.querySelectorAll(".o_text_highlight");
        const usedCustomColors = new Set();
        for (const highlight of highlights) {
            const style = getComputedStyle(highlight);
            const color = style.getPropertyValue("--text-highlight-color");
            if (isCSSColor(color)) {
                usedCustomColors.add(rgbaToHex(color).toLowerCase());
            }
        }
        endScan(() => ({
            highlights: highlights.length,
            colors: usedCustomColors.size,
        }));
        return usedCustomColors;
    }

    getSelectedHighlightNodes() {
        return this.dependencies.selection
            .getTargetedNodes()
            .map((n) => closestElement(n, ".o_text_highlight"))
            .filter(Boolean);
    }
    completeHighlightSelection() {
        const targetedNodes = this.dependencies.selection
            .getTargetedNodes()
            .map(
                (n) =>
                    closestElement(n, ".o_text_highlight") ||
                    n?.querySelector?.(".o_text_highlight"),
            );
        let { startContainer, startOffset, endContainer, endOffset, direction } =
            this.dependencies.selection.getEditableSelection();
        log.logic("completeHighlightSelection", () => ({
            targeted: targetedNodes.length,
            direction,
        }));

        if (targetedNodes.length > 0) {
            if (targetedNodes[0]?.matches?.(".o_text_highlight")) {
                const firstTextNode = descendants(targetedNodes[0]).filter(
                    isTextNode,
                )[0];
                startContainer = firstTextNode;
                startOffset = 0;
            }
            if (targetedNodes.at(-1)?.matches?.(".o_text_highlight")) {
                const lastTextNode = descendants(targetedNodes.at(-1))
                    .filter(isTextNode)
                    .at(-1);
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
        log.logic("deleteSelectedHighlight");
        this.dependencies.format.formatSelection("highlight", { applyStyle: false });
        this.updateSelectedHighlight();
    }
}
registry.category("website-plugins").add(HighlightPlugin.id, HighlightPlugin);

formatsSpecs.highlight = {
    isFormatted: (node) => closestElement(node)?.classList.contains("o_text_highlight"),
    hasStyle: (node) => closestElement(node)?.classList.contains("o_text_highlight"),
    addStyle: (node, { highlightId, thicknessToRestore, colorToRestore }) => {
        const styledNode = closestElement(node, ".o_text_highlight");
        if (styledNode) {
            log.logic("highlight addStyle: replace existing highlight", () => ({
                highlightId,
                previous: styledNode.className,
            }));
            formatsSpecs.highlight.removeStyle(styledNode);
            node = styledNode;
        }
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
                Math.round(parseFloat(style.fontSize) * 0.1) + "px",
            );
        }
    },
    removeStyle: (node) => {
        removeClass(
            node,
            ...[...node.classList].filter((cls) => cls.startsWith("o_text_highlight")),
        );
        removeStyle(node, "--text-highlight-width");
        removeStyle(node, "--text-highlight-color");
    },
};

class HighlightToolbarButton extends Component {
    static props = {
        ...toolbarButtonProps,
        highlightConfiguratorProps: Object,
        onClick: Function,
        title: String,
        getSelection: Function,
    };
    static template = xml`
        <button t-ref="root" t-attf-class="btn btn-light o-select-highlight {{this.highlightState.highlightId ? 'active' : ''}}" t-on-click="this.openHighlightConfigurator" t-att-title="this.props.title">
            <i class="fa oi oi-text-effect oi-fw py-1"/>
        </button>
    `;

    setup() {
        useLifecycleLog(log);
        this.highlightState = useState(
            this.props.highlightConfiguratorProps.getHighlightState(),
        );
        this.root = useRef("root");
        this.componentStack = useStackingComponentState();
        this.componentStack.push(HighlightConfigurator, {
            componentStack: this.componentStack,
            ...this.props.highlightConfiguratorProps,
        });
        this.configuratorPopover = usePopover(StackingComponent, {
            env: this.__owl__.childEnv,
            onClose: () => {
                log.lifecycle("HighlightToolbarButton configurator closed", () => ({
                    depth: this.componentStack.stack.length,
                }));
                while (this.componentStack.stack.length > 1) {
                    this.componentStack.pop();
                }
            },
        });
    }
    openHighlightConfigurator() {
        log.lifecycle("HighlightToolbarButton open configurator");
        this.props.onClick();
        this.configuratorPopover.open(this.root.el, {
            stackState: this.componentStack,
            style: "max-height: 300px; width: 262px",
            class: "d-flex flex-column p-2",
        });
    }
}
