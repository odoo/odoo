import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { Component, xml, useRef, reactive } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { registry } from "@web/core/registry";
import { HighlightConfigurator } from "./highlight_configurator";
import { StackingComponent, useStackingComponentState } from "./stacking_component";
import { formatsSpecs } from "@html_editor/utils/formatting";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { removeStyle } from "@html_editor/utils/dom";
import { isTextNode } from "@html_editor/utils/dom_info";
import { omit } from "@web/core/utils/objects";

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
                    applyHighlight: this.applyHighlight.bind(this),
                    previewHighlight: this.previewHighlight.bind(this),
                    revertHighlight: this.revertHighlight.bind(this),
                    applyHighlightStyle: this.applyHighlightStyle.bind(this),
                    previewHighlightStyle: this.previewHighlightStyle.bind(this),
                    revertHighlightStyle: this.revertHighlightStyle.bind(this),
                    getHighlightState: () => this.highlightState,
                },
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
                if (!svg.closest("[data-highlight-text]")) {
                    svg.remove();
                }
            }
        },
        selectionchange_handlers: this.updateSelectedHighlight.bind(this),
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
        const nodes = this.dependencies.selection.getTraversedNodes().filter(isTextNode);
        if (nodes.length === 0) {
            return;
        }
        const el = closestElement(nodes[0]);
        if (!el) {
            return;
        }
        this.highlightState.highlightId = el.dataset.highlightText;
        if (this.highlightState.highlightId) {
            const style = getComputedStyle(el);
            this.highlightState.color = style.getPropertyValue("--text-highlight-color");
            const thickness = style.getPropertyValue("--text-highlight-width");
            this.highlightState.thickness = thickness ? parseInt(thickness) : "";
        }
    }

    _applyHighlight(highlightId) {
        const highlightedNodes = new Set(
            this.dependencies.selection
                .getTraversedNodes()
                .map((n) => {
                    const el = n.nodeType === Node.ELEMENT_NODE ? n : n.parentElement;
                    return el.closest("[data-highlight-text]");
                })
                .filter(Boolean)
        );
        for (const node of highlightedNodes) {
            for (const svg of node.querySelectorAll(".o_text_highlight_svg")) {
                svg.remove();
            }
        }
        this.dependencies.format.formatSelection("highlight", {
            formatProps: { highlightId },
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
        const highlightedNodes = new Set(
            this.dependencies.selection
                .getTraversedNodes()
                .map((n) => {
                    const el = n.nodeType === Node.ELEMENT_NODE ? n : n.parentElement;
                    return el.closest("[data-highlight-text]");
                })
                .filter(Boolean)
        );
        for (const node of highlightedNodes) {
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
}
registry.category("website-plugins").add(HighlightPlugin.id, HighlightPlugin);

// Todo: formatsSpecs should allow to be register new formats through resources.
formatsSpecs.highlight = {
    isFormatted: (node) => {
        const ret = !!closestElement(node)?.getAttribute("data-highlight-text");
        return ret;
    },
    hasStyle: (node) => {
        const ret = closestElement(node)?.getAttribute("data-highlight-text");
        return ret;
    },
    addStyle: (node, { highlightId }) => {
        node.dispatchEvent(new Event("text_highlight_added", { bubbles: true }));
        node.setAttribute("data-highlight-text", highlightId);
    },
    removeStyle: (node) => {
        node.removeAttribute("data-highlight-text");
        removeStyle(node, "--text-highlight-width");
        removeStyle(node, "--text-highlight-color");
    },
};

class HighlightToolbarButton extends Component {
    static props = {
        applyHighlight: Function,
        applyHighlightStyle: Function,
        getHighlightState: Function,
        getSelection: Function,
        previewHighlight: Function,
        previewHighlightStyle: Function,
        revertHighlight: Function,
        revertHighlightStyle: Function,
        title: String,
    };
    static template = xml`
        <button t-ref="root" class="btn btn-light" t-on-click="openHighlightConfigurator">
            <i class="fa oi oi-text-effect oi-fw py-1"/>
        </button>
    `;

    setup() {
        this.root = useRef("root");
        this.componentStack = useStackingComponentState();
        this.componentStack.push(HighlightConfigurator, {
            componentStack: this.componentStack,
            ...omit(this.props, "title"),
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
        this.configuratorPopover.open(this.root.el, {
            stackState: this.componentStack,
            style: "height: 275px; width: 262px",
            class: "d-flex flex-column",
        });
    }
}
