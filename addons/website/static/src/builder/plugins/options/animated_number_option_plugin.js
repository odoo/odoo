import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { closestElement } from "@html_editor/utils/dom_traversal";

const ANIMATED_NUMBER_SELECTOR = ".s_animated_number";
const DISPLAY_SELECTOR = ".s_animated_number_display";
const VALUE_SELECTOR = ".s_animated_number_value";

class AnimatedNumberOptionPlugin extends Plugin {
    static id = "animatedNumberOption";
    static dependencies = ["selection"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        so_content_addition_selectors: [ANIMATED_NUMBER_SELECTOR],
        is_unremovable_selectors: `${DISPLAY_SELECTOR}, ${VALUE_SELECTOR}`,
        is_node_removable_predicates: (node) => (this.getValueElement(node) ? false : undefined),
        can_format_content_predicates: this.canFormatContent.bind(this),
        formattable_node_providers: this.getStyleTargetElement.bind(this),
        is_formattable_node_predicates: (node) => (this.getValueElement(node) ? true : undefined),
        is_node_editable_predicates: (node) => (this.getValueElement(node) ? true : undefined),
        can_have_scroll_effect_predicates: (el) => !el.matches(ANIMATED_NUMBER_SELECTOR),
    };

    getValueElement(node) {
        return closestElement(node, VALUE_SELECTOR);
    }

    getStyleTargetElement(node, options) {
        const valueEl = this.getValueElement(node);
        if (["underline", "strikeThrough"].includes(options?.formatSpec.id)) {
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
}

registry.category("website-plugins").add(AnimatedNumberOptionPlugin.id, AnimatedNumberOptionPlugin);
