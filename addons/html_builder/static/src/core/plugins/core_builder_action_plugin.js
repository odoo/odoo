import { Plugin } from "@html_editor/plugin";
import { CSS_SHORTHANDS, areCssValuesEqual } from "@html_builder/utils/utils_css";

export class CoreBuilderActionPlugin extends Plugin {
    static id = "CoreBuilderAction";
    resources = {
        builder_actions: this.getActions(),
        builder_style_actions: this.getStyleActions(),
    };

    setup() {
        this.customStyleActions = {};
        for (const styleActions of this.getResource("builder_style_actions")) {
            for (const [actionId, action] of Object.entries(styleActions)) {
                if (actionId in this.customStyleActions) {
                    throw new Error(`Duplicate builder action id: ${action.id}`);
                }
                this.customStyleActions[actionId] = { id: actionId, ...action };
            }
        }
        Object.freeze(this.customStyleActions);
    }

    getActions() {
        return {
            classAction,
            styleAction: this.getStyleAction(),
            attributeAction,
            dataAttributeAction,
            setClassRange,
        };
    }

    getStyleAction() {
        const getValue = ({ editingElement, param: styleName }) => {
            const customStyle = this.customStyleActions[styleName];
            if (customStyle) {
                return customStyle.getValue(editingElement);
            } else {
                return getComputedStyle(editingElement).getPropertyValue(styleName);
            }
        };
        return {
            getValue,
            isApplied: ({ editingElement, param, value }) => {
                const currentValue = getValue({ editingElement, param });
                return currentValue === value;
            },
            apply: ({ editingElement, param: styleName, value }) => {
                // Always reset the inline style first to not put inline style on an
                // element which already has this style through css stylesheets.
                const cssProps = CSS_SHORTHANDS[styleName] || [styleName];
                for (const cssProp of cssProps) {
                    editingElement.style.setProperty(cssProp, "");
                }
                const customStyle = this.customStyleActions[styleName];
                if (customStyle) {
                    customStyle?.apply(editingElement, value);
                } else {
                    const styles = window.getComputedStyle(editingElement);
                    if (!areCssValuesEqual(styles.getPropertyValue(styleName), value, styleName)) {
                        editingElement.style.setProperty(styleName, value, "important");
                    }
                }
            },
        };
    }

    getStyleActions() {
        return styleMap;
    }
}

function getNumericStyle(styleName) {
    return {
        getValue: (editingElement) =>
            parseInt(getComputedStyle(editingElement).getPropertyValue(styleName)).toString(),
        apply: (editingElement, value) => {
            editingElement.style.setProperty(styleName, value, "important");
        },
    };
}

function getNumericStyleWithClass(styleName, className) {
    const action = getNumericStyle(styleName);
    return {
        ...action,
        apply: (editingElement, value) => {
            const parsedValue = parseInt(value);
            const hasBorderClass = editingElement.classList.contains(className);
            if (!parsedValue || parsedValue < 0) {
                if (hasBorderClass) {
                    editingElement.classList.remove(className);
                }
            } else {
                if (!hasBorderClass) {
                    editingElement.classList.add(className);
                }
            }
            action.apply(editingElement, value);
        },
    };
}

const styleMap = {
    "border-width": getNumericStyleWithClass("border-width", "border"),
    "border-radius": getNumericStyleWithClass("border-radius", "rounded"),
    // todo: handle all the other styles
    padding: getNumericStyle("padding"),
};

export const classAction = {
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
};

const attributeAction = {
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
};

const dataAttributeAction = {
    getValue: ({ editingElement, param: attributeName }) => editingElement.dataset[attributeName],
    isApplied: ({ editingElement, param: attributeName, value }) => {
        if (value) {
            return editingElement.dataset[attributeName] === value;
        } else {
            return !(attributeName in editingElement.dataset);
        }
    },
    apply: ({ editingElement, param: attributeName, value }) => {
        if (value) {
            editingElement.dataset[attributeName] = value;
        } else {
            delete editingElement.dataset[attributeName];
        }
    },
    clean: ({ editingElement, param: attributeName }) => {
        delete editingElement.dataset[attributeName];
    },
};

// TODO maybe find a better place for this
const setClassRange = {
    getValue: ({ editingElement, param: classNames }) => {
        for (const index in classNames) {
            const className = classNames[index];
            if (editingElement.classList.contains(className)) {
                return index;
            }
        }
    },
    apply: ({ editingElement, param: classNames, value: index }) => {
        for (const className of classNames) {
            if (editingElement.classList.contains(className)) {
                editingElement.classList.remove(className);
            }
        }
        editingElement.classList.add(classNames[index]);
    },
};
