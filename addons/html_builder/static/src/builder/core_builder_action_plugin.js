import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class CoreBuilderActionPlugin extends Plugin {
    static id = "CoreBuilderAction";
    resources = {
        builder_actions: actions,
    };
}
registry.category("website-plugins").add(CoreBuilderActionPlugin.id, CoreBuilderActionPlugin);

const styleMap = {
    borderWidth: {
        getValue: (editingElement) => {
            return parseInt(
                getComputedStyle(editingElement).getPropertyValue("border-width")
            ).toString();
        },
        apply: (editingElement, value) => {
            const parsedValue = parseInt(value);
            const hasBorderClass = editingElement.classList.contains("border");
            if (!parsedValue || parsedValue < 0) {
                if (hasBorderClass) {
                    editingElement.classList.remove("border");
                }
            } else {
                if (!hasBorderClass) {
                    editingElement.classList.add("border");
                }
            }
            editingElement.style.setProperty("border-width", `${parsedValue}px`, "important");
        },
    },
};

const actions = {
    classAction: {
        isActive: ({ editingElement, param: className }) => {
            return editingElement.classList.contains(className);
        },
        apply: ({ editingElement, param: className, value }) => {
            editingElement.classList.add(className);
        },
        clean: ({ editingElement, param: className, value }) => {
            editingElement.classList.remove(className);
        },
    },
    styleAction: {
        getValue: ({ editingElement, param: styleName }) => {
            const customStyle = styleMap[styleName];
            if (customStyle) {
                return customStyle.getValue(editingElement);
            } else {
                return getComputedStyle(editingElement).getPropertyValue(styleName);
            }
        },
        apply: ({ editingElement, param: styleName, value }) => {
            const customStyle = styleMap[styleName];
            if (customStyle) {
                customStyle?.apply(editingElement, value);
            } else {
                editingElement.style.setProperty(styleName, value);
            }
        },
    },
    attributeAction: {
        getValue: ({ editingElement, param: attributeName }) => {
            return editingElement.getAttribute(attributeName);
        },
        isActive: ({ editingElement, param: attributeName, value }) => {
            if (value) {
                return (
                    editingElement.hasAttribute(attributeName) &&
                    editingElement.getAttribute(attributeName) === value
                );
            } else {
                return !editingElement.hasAttribute(attributeName);
            }
        },
        apply: ({ editingElement, param: attributeName, value }) => {
            if (value) {
                editingElement.setAttribute(attributeName, value);
            } else {
                editingElement.removeAttribute(attributeName);
            }
        },
        clean: ({ editingElement, param: attributeName }) => {
            editingElement.removeAttribute(attributeName);
        },
    },
};
