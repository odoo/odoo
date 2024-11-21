import { registry } from "@web/core/registry";

registry.category("website-builder-actions").add("classAction", {
    isActive: ({ editingElement, param: className }) => {
        return editingElement.classList.contains(className);
    },
    apply: ({ editingElement, param: className, value }) => {
        editingElement.classList.add(className);
    },
    clean: ({ editingElement, param: className, value }) => {
        editingElement.classList.remove(className);
    },
});

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

registry.category("website-builder-actions").add("styleAction", {
    getValue: ({ editingElement, param: styleName }) => {
        return styleMap[styleName]?.getValue(editingElement);
    },
    apply: ({ editingElement, param: styleName, value }) => {
        styleMap[styleName]?.apply(editingElement, value);
    },
});

registry.category("website-builder-actions").add("attributeAction", {
    isActive: ({ editingElement, param: attributeName, value }) => {
        if (value) {
            return editingElement.hasAttribute(attributeName);
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
});
