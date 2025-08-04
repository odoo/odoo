import { Plugin } from "@html_editor/plugin";
import { getHtmlStyle } from "@html_editor/utils/formatting";
import {
    CSS_SHORTHANDS,
    applyNeededCss,
    areCssValuesEqual,
    normalizeColor,
} from "@html_builder/utils/utils_css";
import { BuilderAction } from "@html_builder/core/builder_action";
import { getValueFromVar } from "@html_builder/utils/utils";

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
        builder_actions: {
            ClassAction,
            AttributeAction,
            StyleAction,
            DataAttributeAction,
            SetClassRangeAction,
        },
        system_classes: ["o_we_force_no_transition"],
    };
}

function getStyleValue(el, styleName) {
    const computedStyle = window.getComputedStyle(el);
    const cssProps = CSS_SHORTHANDS[styleName] || [styleName];
    const cssValues = cssProps.map((cssProp) => computedStyle.getPropertyValue(cssProp).trim());
    if (
        cssValues.length === 4 &&
        areCssValuesEqual(cssValues[3], cssValues[1], styleName, computedStyle)
    ) {
        cssValues.pop();
    }
    if (
        cssValues.length === 3 &&
        areCssValuesEqual(cssValues[2], cssValues[0], styleName, computedStyle)
    ) {
        cssValues.pop();
    }
    if (
        cssValues.length === 2 &&
        areCssValuesEqual(cssValues[1], cssValues[0], styleName, computedStyle)
    ) {
        cssValues.pop();
    }
    return cssValues.join(" ");
}

function setStyle(el, styleName, value, { extraClass, force = false, allowImportant = true } = {}) {
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

export class ClassAction extends BuilderAction {
    static id = "classAction";
    getPriority({ params: { mainParam: classNames } = {} }) {
        return (classNames || "")?.trim().split(/\s+/).filter(Boolean).length || 0;
    }
    isApplied({ editingElement, params: { mainParam: classNames } = {} }) {
        if (classNames === undefined || classNames === "") {
            return true;
        }
        return classNames
            .split(" ")
            .every((className) => editingElement.classList.contains(className));
    }
    apply({ editingElement, params: { mainParam: classNames } = {} }) {
        for (const className of (classNames || "").split(" ")) {
            if (className !== "") {
                editingElement.classList.add(className);
            }
        }
    }
    clean({ editingElement, params: { mainParam: classNames } = {} }) {
        for (const className of (classNames || "").split(" ")) {
            if (className !== "") {
                editingElement.classList.remove(className);
            }
        }
    }
}

class AttributeAction extends BuilderAction {
    static id = "attributeAction";
    getValue({ editingElement, params: { mainParam: attributeName } = {} }) {
        return editingElement.getAttribute(attributeName);
    }
    isApplied({ editingElement, params: { mainParam: attributeName } = {}, value }) {
        if (value) {
            return (
                editingElement.hasAttribute(attributeName) &&
                editingElement.getAttribute(attributeName) === value
            );
        } else {
            return !editingElement.hasAttribute(attributeName);
        }
    }
    apply({ editingElement, params: { mainParam: attributeName } = {}, value }) {
        if (value) {
            editingElement.setAttribute(attributeName, value);
        } else {
            editingElement.removeAttribute(attributeName);
        }
    }
    clean({ editingElement, params: { mainParam: attributeName } = {} }) {
        editingElement.removeAttribute(attributeName);
    }
}

class DataAttributeAction extends BuilderAction {
    static id = "dataAttributeAction";
    getValue({ editingElement, params: { mainParam: attributeName } = {} }) {
        if (!/(^color|Color)($|(?=[A-Z]))/.test(attributeName)) {
            return editingElement.dataset[attributeName];
        }
        const color = normalizeColor(
            editingElement.dataset[attributeName],
            getHtmlStyle(this.document)
        );
        return color;
    }
    isApplied({ editingElement, params: { mainParam: attributeName } = {}, value }) {
        if (value) {
            value = getValueFromVar(value.toString());
            return editingElement.dataset[attributeName] === value;
        } else {
            return !(attributeName in editingElement.dataset);
        }
    }
    apply({ editingElement, params: { mainParam: attributeName } = {}, value }) {
        if (value) {
            value = getValueFromVar(value.toString());
            editingElement.dataset[attributeName] = value;
        } else {
            delete editingElement.dataset[attributeName];
        }
    }
    clean({ editingElement, params: { mainParam: attributeName } = {} }) {
        delete editingElement.dataset[attributeName];
    }
}

// TODO maybe find a better place for this
class SetClassRangeAction extends BuilderAction {
    static id = "setClassRange";
    getValue({ editingElement, params: { mainParam: classNames } }) {
        for (const index in classNames) {
            const className = classNames[index];
            if (editingElement.classList.contains(className)) {
                return index;
            }
        }
    }
    apply({ editingElement, params: { mainParam: classNames }, value: index }) {
        for (const className of classNames) {
            if (editingElement.classList.contains(className)) {
                editingElement.classList.remove(className);
            }
        }
        editingElement.classList.add(classNames[index]);
    }
}

export class StyleAction extends BuilderAction {
    static id = "styleAction";
    static dependencies = ["color"];
    getValue({ editingElement: el, params: { mainParam: styleName } }) {
        if (styleName === "--box-border-width"
                || CSS_SHORTHANDS["--box-border-width"].includes(styleName)
                || styleName === "--box-border-radius"
                || CSS_SHORTHANDS["--box-border-radius"].includes(styleName)) {
            // When reading a CSS variable, we need to get the computed value
            // of the actual property it controls, ideally. Not only because the
            // panel should reflect what the user actually sees but also because
            // the user could have forced its own inline style by himself. Also,
            // by compatibility with how borders were edited in the past.
            // See CSS_VARIABLE_EDIT_TODO.
            //
            // TODO this should probably be more generic. Note that this was
            // also done as a fix where reading the actual CSS variable value
            // was simply not working properly because getStyleValue checks the
            // CSS_SHORTHANDS which obviously do not magically work.
            styleName = styleName.substring("--box-".length);
        }

        if (styleName === "box-shadow") {
            const value = getStyleValue(el, styleName);
            const inset = value.includes("inset");
            let values = value.replace(/,\s/g, ",").replace("inset", "").trim().split(/\s+/g);
            const color = values.find((s) => !s.match(/^\d/));
            values = values.join(" ").replace(color, "").trim();
            return `${color} ${values}${inset ? " inset" : ""}`;
        } else if (
            styleName === "border-width" ||
            CSS_SHORTHANDS["border-width"].includes(styleName)
        ) {
            let value = getStyleValue(el, styleName);
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
        } else if (styleName === "row-gap" || styleName === "column-gap") {
            return parseInt(getStyleValue(el, styleName)) || 0;
        } else if (styleName === "width") {
            return el.style.width;
        } else if (styleName === "background-color") {
            return this.dependencies.color.getElementColors(el)["backgroundColor"];
        } else if (styleName === "color") {
            return this.dependencies.color.getElementColors(el)["color"];
        }
        return this._getValueWithoutTransition(el, styleName);
    }
    isApplied({ editingElement: el, params: { mainParam: styleName }, value }) {
        const currentValue = this.getValue({
            editingElement: el,
            params: { mainParam: styleName },
        });
        return currentValue === value;
    }
    apply({ editingElement, params = {}, value }) {
        if (!this.delegateTo("apply_custom_css_style", { editingElement, params, value })) {
            this.applyCssStyle({ editingElement, params, value });
        }
    }
    applyCssStyle({ editingElement, params = {}, value }) {
        params = { ...params };
        const styleName = params.mainParam;
        delete params.mainParam;
        // Disable all transitions for the duration of the method as many
        // comparisons will be done on the element to know if applying a
        // property has an effect or not. Also, changing a css property via the
        // editor should not show any transition as previews would not be done
        // immediately, which is not good for the user experience.
        withoutTransition(editingElement, () => {
            setStyle(editingElement, styleName, value, params);
        });
    }
    _getValueWithoutTransition(el, styleName) {
        return withoutTransition(el, () => getStyleValue(el, styleName));
    }
}
