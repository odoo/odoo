import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { CSS_SHORTHANDS, areCssValuesEqual } from "@html_builder/builder/utils/utils_css";

class CoreBuilderActionPlugin extends Plugin {
    static id = "CoreBuilderAction";
    resources = {
        builder_actions: coreBuilderActions,
    };
}
registry.category("website-plugins").add(CoreBuilderActionPlugin.id, CoreBuilderActionPlugin);

function getNumericStyle(styleName) {
    return {
        getValue: (editingElement) =>
            parseInt(getComputedStyle(editingElement).getPropertyValue(styleName)).toString(),
        apply: (editingElement, value) => {
            editingElement.style.setProperty(styleName, `${parseInt(value)}px`, "important");
        },
    };
}

const styleMap = {
    borderWidth: {
        getValue: (editingElement) =>
            parseInt(getComputedStyle(editingElement).getPropertyValue("border-width")).toString(),
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
    // todo: handle all the other styles
    padding: getNumericStyle("padding"),
};

export const coreBuilderActions = {
    classAction: {
        getPriority: ({ param: classNames = "" }) =>
            classNames?.trim().split(/\s+/).filter(Boolean).length || 0,
        isApplied: ({ editingElement, param: classNames }) => {
            if (classNames === "") {
                return true;
            }
            return classNames
                .split(" ")
                .every((className) => editingElement.classList.contains(className));
        },
        apply: ({ editingElement, param: classNames }) => {
            for (const className of classNames.split(" ")) {
                if (className !== "") {
                    editingElement.classList.add(className);
                }
            }
        },
        clean: ({ editingElement, param: classNames }) => {
            for (const className of classNames.split(" ")) {
                if (className !== "") {
                    editingElement.classList.remove(className);
                }
            }
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
        isApplied: ({ editingElement, param, value }) => {
            const currentValue = coreBuilderActions.styleAction.getValue({ editingElement, param });
            return currentValue === value;
        },
        apply: ({ editingElement, param: styleName, value }) => {
            // Always reset the inline style first to not put inline style on an
            // element which already has this style through css stylesheets.
            const cssProps = CSS_SHORTHANDS[styleName] || [styleName];
            for (const cssProp of cssProps) {
                editingElement.style.setProperty(cssProp, "");
            }
            const customStyle = styleMap[styleName];
            if (customStyle) {
                customStyle?.apply(editingElement, value);
            } else {
                const styles = window.getComputedStyle(editingElement);
                if (!areCssValuesEqual(styles.getPropertyValue(styleName), value, styleName)) {
                    editingElement.style.setProperty(styleName, value, "important");
                }
            }
        },
    },
    attributeAction: {
        getValue: ({ editingElement, param: attributeName }) =>
            editingElement.getAttribute(attributeName),
        isApplied: ({ editingElement, param: attributeName, value }) => {
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
