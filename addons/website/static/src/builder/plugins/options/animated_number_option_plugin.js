import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { closestElement, descendants } from "@html_editor/utils/dom_traversal";

const ANIMATED_NUMBER_SELECTOR = ".s_animated_number";
const DISPLAY_SELECTOR = ".s_animated_number_display";
const VALUE_SELECTOR = ".s_animated_number_value";

class AnimatedNumberOptionPlugin extends Plugin {
    static id = "animatedNumberOption";
    static dependencies = ["color", "selection"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        so_content_addition_selectors: [ANIMATED_NUMBER_SELECTOR],
        is_unremovable_selectors: `${DISPLAY_SELECTOR}, ${VALUE_SELECTOR}`,
        is_node_removable_predicates: (node) => (this.getValueElement(node) ? false : undefined),
        apply_color_overrides: this.applyColorToAnimatedNumberValues.bind(this),
        can_format_content_predicates: this.canFormatContent.bind(this),
        color_target_providers: this.getStyleTargetElement.bind(this),
        formattable_node_providers: this.getStyleTargetElement.bind(this),
        is_formattable_node_predicates: (node) => (this.getValueElement(node) ? true : undefined),
        is_node_editable_predicates: (node) => (this.getValueElement(node) ? true : undefined),
        can_have_scroll_effect_predicates: (el) => !el.matches(ANIMATED_NUMBER_SELECTOR),
    };

    getValueElement(node) {
        return closestElement(node, VALUE_SELECTOR);
    }

    getStyleTargetElement(node, formatName) {
        const valueEl = this.getValueElement(node);
        if (["underline", "strikeThrough"].includes(formatName)) {
            return valueEl;
        }
        const displayEl = closestElement(node, DISPLAY_SELECTOR);
        if (
            displayEl &&
            ((displayEl.childNodes.length === 1 && displayEl.firstChild === valueEl) ||
                this.dependencies.selection.areNodeContentsFullySelected(displayEl))
        ) {
            return displayEl;
        }
        return valueEl;
    }

    canFormatContent(selection) {
        const { anchorNode, focusNode } = selection;
        if (anchorNode === focusNode && this.getValueElement(anchorNode)) {
            return true;
        }
    }

    applyColorToAnimatedNumberValues(color, mode, coloredNodes) {
        const targetElements = new Set(
            this.dependencies.selection
                .getTargetedNodes()
                .map((node) => this.getStyleTargetElement(node))
                .filter(Boolean)
        );
        for (const targetEl of targetElements) {
            const targetDescendants = descendants(targetEl);
            if (targetEl.matches(DISPLAY_SELECTOR)) {
                for (const node of targetDescendants) {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        this.dependencies.color.colorElement(node, "", mode);
                    }
                }
            }
            this.dependencies.color.colorElement(targetEl, color, mode);
            [targetEl, ...targetDescendants].forEach((node) => coloredNodes.add(node));
        }
    }
}

registry.category("website-plugins").add(AnimatedNumberOptionPlugin.id, AnimatedNumberOptionPlugin);
