import { Plugin } from "@html_editor/plugin";
import { CSS_SHORTHANDS, applyNeededCss, areCssValuesEqual } from "@html_builder/utils/utils_css";

export function withoutTransition(editingElement, callback) {
    if (editingElement.classList.contains("o_we_force_no_transition")) {
        return callback();
    }
    editingElement.classList.add("o_we_force_no_transition");
    try {
        return callback();
    } finally {
        editingElement.classList.remove("o_we_force_no_transition");
    }
}

export class CoreBuilderActionPlugin extends Plugin {
    static id = "coreBuilderAction";
    resources = {
        builder_actions: this.getActions(),
        builder_style_actions: this.getStyleActions(),
        system_classes: ["o_we_force_no_transition"],
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

    getStyleActions() {
        const styleActions = {
            "box-shadow": {
                getValue: ({ editingElement: el, param }) => {
                    const value = getStyleValue(el, param);
                    const inset = value.includes("inset");
                    let values = value
                        .replace(/,\s/g, ",")
                        .replace("inset", "")
                        .trim()
                        .split(/\s+/g);
                    const color = values.find((s) => !s.match(/^\d/));
                    values = values.join(" ").replace(color, "").trim();
                    return `${color} ${values}${inset ? " inset" : ""}`;
                },
                apply: setStyleValue,
            },
            "border-width": {
                getValue: ({ editingElement: el, param }) => {
                    let value = getStyleValue(el, param);
                    if (value.endsWith("px")) {
                        value = value
                            .split(/\s+/g)
                            .map(
                                (singleValue) =>
                                    // Rounding value up avoids zoom-in issues.
                                    // Zoom-out issues are not an expected use case.
                                    `${Math.ceil(parseFloat(singleValue))}px`
                            )
                            .join(" ");
                    }
                    return value;
                },
                apply: setStyleValue,
            },
            "row-gap": {
                getValue: ({ editingElement: el, param }) =>
                    parseInt(getStyleValue(el, param)) || 0,
                apply: setStyleValue,
            },
            "column-gap": {
                getValue: ({ editingElement: el, param, value }) =>
                    parseInt(getStyleValue(el, param)) || 0,
                apply: setStyleValue,
            },
            width: {
                // using inline style instead of computed because of the
                // messy %-px convertion and the messy auto keyword).
                getValue: ({ editingElement: el, param, value }) => el.style.width,
                apply: setStyleValue,
            },
        };
        for (const borderWidthPropery of CSS_SHORTHANDS["border-width"]) {
            styleActions[borderWidthPropery] = styleActions["border-width"];
        }
        return styleActions;
    }

    getStyleAction() {
        const getValue = (...args) => {
            const { editingElement, param } = args[0];
            // Disable all transitions for the duration of the style check
            // as we want to know the final value of a property to properly
            // update the UI.
            return withoutTransition(editingElement, () => {
                const customStyle = this.customStyleActions[param.mainParam];
                if (customStyle) {
                    return customStyle.getValue(...args);
                } else {
                    return getStyleValue(editingElement, param);
                }
            });
        };
        return {
            getValue,
            isApplied: ({ editingElement, param = {}, value }) => {
                const currentValue = getValue({ editingElement, param });
                return currentValue === value;
            },
            apply: (...args) => {
                const { editingElement, param = {}, value } = args[0];
                // Disable all transitions for the duration of the method as many
                // comparisons will be done on the element to know if applying a
                // property has an effect or not. Also, changing a css property via the
                // editor should not show any transition as previews would not be done
                // immediately, which is not good for the user experience.
                withoutTransition(editingElement, () => {
                    const customStyle = this.customStyleActions[param.mainParam];
                    if (customStyle) {
                        customStyle.apply(...args);
                    } else {
                        setStyleValue({ editingElement, param, value });
                    }
                });
            },
            // TODO clean() is missing !!
        };
    }
}

function getStyleValue(el, { mainParam: styleName } = {}) {
    const computedStyle = window.getComputedStyle(el);
    const cssProps = CSS_SHORTHANDS[styleName] || [styleName];
    const cssValues = cssProps.map((cssProp) => computedStyle.getPropertyValue(cssProp).trim());
    if (cssValues.length === 4 && areCssValuesEqual(cssValues[3], cssValues[1], styleName)) {
        cssValues.pop();
    }
    if (cssValues.length === 3 && areCssValuesEqual(cssValues[2], cssValues[0], styleName)) {
        cssValues.pop();
    }
    if (cssValues.length === 2 && areCssValuesEqual(cssValues[1], cssValues[0], styleName)) {
        cssValues.pop();
    }
    return cssValues.join(" ");
}

function setStyleValue({
    editingElement: el,
    param: { mainParam: styleName, extraClass, force = false, allowImportant = true } = {},
    value,
}) {
    const computedStyle = window.getComputedStyle(el);
    const cssProps = CSS_SHORTHANDS[styleName] || [styleName];
    // Always reset the inline style first to not put inline style on an
    // element which already has this style through css stylesheets.
    for (const cssProp of cssProps) {
        el.style.setProperty(cssProp, "");
    }
    el.classList.remove(extraClass);

    // Replacing ', ' by ',' to prevent attributes with internal space separators from being split:
    // eg: "rgba(55, 12, 47, 1.9) 47px" should be split as ["rgba(55,12,47,1.9)", "47px"]
    const values = value.replace(/,\s/g, ",").split(/\s+/g);
    // Compute missing values:
    // "a" => "a a a a"
    // "a b" => "a b a b"
    // "a b c" => "a b c b"
    // "a b c d" => "a b c d d d d"
    while (values.length < cssProps.length) {
        const len = values.length;
        const index = len == 3 ? 1 : len == 1 || len == 2 ? 0 : len - 1;
        values.push(values[index]);
    }

    let hasUserValue = false;
    const applyAllCSS = (values) => {
        for (let i = cssProps.length - 1; i > 0; i--) {
            hasUserValue =
                applyNeededCss(el, cssProps[i], values.pop(), computedStyle, {
                    force,
                    allowImportant,
                }) || hasUserValue;
        }
        hasUserValue =
            applyNeededCss(el, cssProps[0], values.join(" "), computedStyle, {
                force,
                allowImportant,
            }) || hasUserValue;
    };
    applyAllCSS([...values]);

    if (extraClass) {
        el.classList.toggle(extraClass, hasUserValue);
        if (hasUserValue) {
            // Might have changed because of the class.
            for (const cssProp of cssProps) {
                el.style.removeProperty(cssProp);
            }
            applyAllCSS(values);
        }
    }
}

export function getGeneralStyle(param) {
    return {
        getValue: (editingElement) => getStyleValue(editingElement, param),
        apply: setStyleValue,
    };
}

export const classAction = {
    getPriority: ({ param: { mainParam: classNames } = {} }) =>
        (classNames || "")?.trim().split(/\s+/).filter(Boolean).length || 0,
    isApplied: ({ editingElement, param: { mainParam: classNames } = {} }) => {
        if (classNames === undefined || classNames === "") {
            return true;
        }
        return classNames
            .split(" ")
            .every((className) => editingElement.classList.contains(className));
    },
    apply: ({ editingElement, param: { mainParam: classNames } = {} }) => {
        for (const className of (classNames || "").split(" ")) {
            if (className !== "") {
                editingElement.classList.add(className);
            }
        }
    },
    clean: ({ editingElement, param: { mainParam: classNames } = {} }) => {
        for (const className of (classNames || "").split(" ")) {
            if (className !== "") {
                editingElement.classList.remove(className);
            }
        }
    },
};

const attributeAction = {
    getValue: ({ editingElement, param: { mainParam: attributeName } = {} }) =>
        editingElement.getAttribute(attributeName),
    isApplied: ({ editingElement, param: { mainParam: attributeName } = {}, value }) => {
        if (value) {
            return (
                editingElement.hasAttribute(attributeName) &&
                editingElement.getAttribute(attributeName) === value
            );
        } else {
            return !editingElement.hasAttribute(attributeName);
        }
    },
    apply: ({ editingElement, param: { mainParam: attributeName } = {}, value }) => {
        if (value) {
            editingElement.setAttribute(attributeName, value);
        } else {
            editingElement.removeAttribute(attributeName);
        }
    },
    clean: ({ editingElement, param: { mainParam: attributeName } = {} }) => {
        editingElement.removeAttribute(attributeName);
    },
};

const dataAttributeAction = {
    getValue: ({ editingElement, param: { mainParam: attributeName } = {} }) =>
        editingElement.dataset[attributeName],
    isApplied: ({ editingElement, param: { mainParam: attributeName } = {}, value }) => {
        if (value) {
            return editingElement.dataset[attributeName] === value;
        } else {
            return !(attributeName in editingElement.dataset);
        }
    },
    apply: ({ editingElement, param: { mainParam: attributeName } = {}, value }) => {
        if (value) {
            editingElement.dataset[attributeName] = value;
        } else {
            delete editingElement.dataset[attributeName];
        }
    },
    clean: ({ editingElement, param: { mainParam: attributeName } = {} }) => {
        delete editingElement.dataset[attributeName];
    },
};

// TODO maybe find a better place for this
const setClassRange = {
    getValue: ({ editingElement, param: { mainParam: classNames } }) => {
        for (const index in classNames) {
            const className = classNames[index];
            if (editingElement.classList.contains(className)) {
                return index;
            }
        }
    },
    apply: ({ editingElement, param: { mainParam: classNames }, value: index }) => {
        for (const className of classNames) {
            if (editingElement.classList.contains(className)) {
                editingElement.classList.remove(className);
            }
        }
        editingElement.classList.add(classNames[index]);
    },
};
