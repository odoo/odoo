import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { getFontSizeOrClass } from "@html_editor/utils/formatting";
import { ClassAction } from "@html_builder/core/core_builder_action_plugin";
import { BG_CLASSES_REGEX, TEXT_CLASSES_REGEX } from "@html_editor/utils/color";

class AnimatedNumberOptionPlugin extends Plugin {
    static id = "animatedNumberOption";
    static dependencies = ["selection"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        so_content_addition_selectors: [".s_animated_number"],
        builder_actions: {
            ToggleTitleAnimatedNumberAction,
        },
        is_unremovable_selectors: ".s_animated_number_display, .s_animated_number_value",
        is_formattable_node_predicates: this.isFormattableNode.bind(this),
        normalize_processors: this.normalize.bind(this),
        can_have_scroll_effect_predicates: (el) => !el.matches(".s_animated_number"),
    };

    isFormattableNode(node) {
        if (closestElement(node, ".s_animated_number_value")) {
            return true;
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
        let afterValueReferenceNode = valueEl;
        for (const textNode of this.getAffixTextNodes(displayEl, fontEl)) {
            const wrapper = this.createAffixStyleWrapper(valueEl, { includeColor: !fontEl });
            if (fontEl) {
                const isBeforeValue = this.isBefore(textNode, valueEl);
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

    isBefore(node, referenceNode) {
        return !!(node.compareDocumentPosition(referenceNode) & Node.DOCUMENT_POSITION_FOLLOWING);
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
                console.log(fontSizeStyle);
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

export class ToggleTitleAnimatedNumberAction extends ClassAction {
    static id = "toggleTitleAnimatedNumber";

    isApplied({ editingElement, value }) {
        if (!value) {
            return !editingElement.querySelector(".s_animated_number_label");
        } else {
            return true;
        }
    }
    apply({ editingElement, value }) {
        editingElement.querySelector(".s_animated_number_label").classList.toggle("d-none", !value);
    }
}

registry.category("website-plugins").add(AnimatedNumberOptionPlugin.id, AnimatedNumberOptionPlugin);
