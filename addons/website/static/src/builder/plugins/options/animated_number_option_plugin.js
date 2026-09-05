import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BG_CLASSES_REGEX, TEXT_CLASSES_REGEX } from "@html_editor/utils/color";
import { closestElement, descendants } from "@html_editor/utils/dom_traversal";
import { getFontSizeOrClass } from "@html_editor/utils/formatting";
import { ClassAction } from "@html_builder/core/core_builder_action_plugin";

class AnimatedNumberOptionPlugin extends Plugin {
    static id = "animatedNumberOption";
    static dependencies = ["color", "selection"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        so_content_addition_selectors: [".s_animated_number"],
        builder_actions: {
            SetAnimatedNumberTitlePositionAction,
        },
        is_unremovable_selectors: ".s_animated_number_display, .s_animated_number_value",
        is_node_removable_predicates: (node) => (this.getValueElement(node) ? false : undefined),
        apply_color_overrides: this.applyColorToAnimatedNumberValues.bind(this),
        can_format_content_predicates: this.canFormatContent.bind(this),
        color_target_providers: this.getValueElement.bind(this),
        formattable_node_providers: this.getValueElement.bind(this),
        is_formattable_node_predicates: (node) => (this.getValueElement(node) ? true : undefined),
        is_node_editable_predicates: (node) => (this.getValueElement(node) ? true : undefined),
        normalize_processors: this.normalize.bind(this),
        can_have_scroll_effect_predicates: (el) => !el.matches(".s_animated_number"),
    };

    getValueElement(node) {
        return closestElement(node, ".s_animated_number_value");
    }

    canFormatContent(selection) {
        const { anchorNode, focusNode } = selection;
        if (anchorNode === focusNode && this.getValueElement(anchorNode)) {
            return true;
        }
    }

    applyColorToAnimatedNumberValues(color, mode, coloredNodes) {
        const valueElements = new Set(
            this.dependencies.selection
                .getTargetedNodes()
                .map((node) => this.getValueElement(node))
                .filter(Boolean)
        );
        for (const valueEl of valueElements) {
            this.dependencies.color.colorElement(valueEl, color, mode);
            [valueEl, ...descendants(valueEl)].forEach((node) => coloredNodes.add(node));
        }
    }

    normalize(root) {
        const displayEl = closestElement(root, ".s_animated_number_display");
        if (!displayEl) {
            return root;
        }
        const valueEl = displayEl.querySelector(".s_animated_number_value");
        if (!valueEl) {
            return root;
        }
        const fontEl =
            valueEl.parentElement?.tagName === "FONT" ? valueEl.parentElement : undefined;
        const affixTextNodes = this.getAffixTextNodes(displayEl, fontEl);
        if (!affixTextNodes.length) {
            return root;
        }
        const selection = this.document.getSelection();
        const shouldPreserveSelection =
            selection?.rangeCount &&
            affixTextNodes.some(
                (textNode) =>
                    selection.anchorNode === textNode ||
                    selection.focusNode === textNode ||
                    (!selection.isCollapsed && selection.getRangeAt(0).intersectsNode(textNode))
            );
        const cursors = shouldPreserveSelection
            ? this.dependencies.selection.preserveSelection()
            : null;
        let afterValueReferenceNode = valueEl;
        for (const textNode of affixTextNodes) {
            const wrapper = this.createAffixStyleWrapper(valueEl, { includeColor: !fontEl });
            if (fontEl) {
                const isBeforeValue = !!(
                    textNode.compareDocumentPosition(valueEl) & Node.DOCUMENT_POSITION_FOLLOWING
                );
                const referenceNode = isBeforeValue ? valueEl : afterValueReferenceNode;
                referenceNode[isBeforeValue ? "before" : "after"](wrapper);
                this.moveTextNodeInWrapper(textNode, wrapper);
                if (!isBeforeValue) {
                    afterValueReferenceNode = wrapper;
                }
            } else {
                textNode.replaceWith(wrapper);
                this.moveTextNodeInWrapper(textNode, wrapper);
            }
        }
        cursors?.restore();
        return root;
    }

    getAffixTextNodes(displayEl, fontEl) {
        return [...displayEl.childNodes].flatMap((node) => {
            if (node === fontEl) {
                return [...fontEl.childNodes].filter((node) => node.nodeType === Node.TEXT_NODE);
            }
            return node.nodeType === Node.TEXT_NODE ? [node] : [];
        });
    }

    moveTextNodeInWrapper(textNode, wrapper) {
        let innermostWrapper = wrapper;
        while (innermostWrapper.firstElementChild) {
            innermostWrapper = innermostWrapper.firstElementChild;
        }
        innermostWrapper.append(textNode);
    }

    createAffixStyleWrapper(valueEl, { includeColor = true } = {}) {
        let wrapper;
        let innermostWrapper;
        const addWrapper = (tagName) => {
            const el = this.document.createElement(tagName);
            if (innermostWrapper) {
                innermostWrapper.append(el);
            } else {
                wrapper = el;
            }
            innermostWrapper = el;
            return el;
        };

        const fontSizeStyle = getFontSizeOrClass(valueEl);
        if (fontSizeStyle.type) {
            const span = addWrapper("span");
            if (fontSizeStyle.type === "font-size") {
                span.style.fontSize = fontSizeStyle.value;
            } else if (fontSizeStyle.type === "class") {
                span.classList.add(fontSizeStyle.value);
            }
        }

        if (includeColor) {
            const colorClasses = [...valueEl.classList].filter(
                (className) =>
                    TEXT_CLASSES_REGEX.test(className) || BG_CLASSES_REGEX.test(className)
            );
            const colorStyles = [
                "color",
                "background-color",
                "background-image",
                "-webkit-text-fill-color",
            ].filter((styleName) => valueEl.style.getPropertyValue(styleName));
            if (colorClasses.length || colorStyles.length) {
                const font = addWrapper("font");
                font.classList.add(...colorClasses);
                for (const styleName of colorStyles) {
                    font.style.setProperty(styleName, valueEl.style.getPropertyValue(styleName));
                }
            }
        }

        for (const [tagName, hasStyle] of [
            ["strong", valueEl.style.fontWeight === "bolder"],
            ["em", valueEl.style.fontStyle === "italic"],
            ["u", this.hasTextDecoration(valueEl, "underline")],
            ["s", this.hasTextDecoration(valueEl, "line-through")],
        ]) {
            if (hasStyle) {
                addWrapper(tagName);
            }
        }

        return wrapper || this.document.createElement("span");
    }

    hasTextDecoration(valueEl, decoration) {
        return [valueEl.style.textDecoration, valueEl.style.textDecorationLine].some((style) =>
            style.split(/\s+/).includes(decoration)
        );
    }
}

export class SetAnimatedNumberTitlePositionAction extends ClassAction {
    static id = "setAnimatedNumberTitlePosition";

    isApplied({ editingElement, value }) {
        const labelEl = editingElement.querySelector(".s_animated_number_label");
        if (!value) {
            return !labelEl || labelEl.classList.contains("d-none");
        }
        return Boolean(
            labelEl && !labelEl.classList.contains("d-none") && super.isApplied(...arguments)
        );
    }

    apply({ editingElement, value }) {
        super.apply(...arguments);
        editingElement
            .querySelector(".s_animated_number_label")
            ?.classList.toggle("d-none", !value);
    }
}

registry.category("website-plugins").add(AnimatedNumberOptionPlugin.id, AnimatedNumberOptionPlugin);
