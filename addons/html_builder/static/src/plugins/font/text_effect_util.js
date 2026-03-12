import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { mixCssColors } from "@web/core/utils/colors";

export const defaults = {
    shadow: "false",
    shadowColor: "rgba(0, 0, 0, 0.5)",
    shadowOffsetX: "5px",
    shadowOffsetY: "5px",
    shadowBlur: "3px",
    outline: "0px",
    outlineColor: "#808080",
    trailCount: "0",
    trailOffsetX: "10px",
    trailOffsetY: "10px",
    trailStartColor: "#2F80ED",
    trailEndColor: "#B2FFDA",
    rotate: "0deg",
    tiltX: "0deg",
    tiltY: "0deg",
    tiltPerspective: "1",
    skewX: "0deg",
    skewY: "0deg",
    moveX: "0%",
    moveY: "0%",
    scale: "100%",
};

export function applyConfiguredEffects(element) {
    let json = {};
    if (element.dataset.textEffect) {
        json = JSON.parse(element.dataset.textEffect);
    }
    const values = Object.assign({}, defaults, json);
    const shadows = [];
    if (json.trailCount) {
        const trailCount = parseInt(values.trailCount);
        const startColor = getActualColor(values.trailStartColor, element.ownerDocument);
        const endColor = getActualColor(values.trailEndColor, element.ownerDocument);
        for (let trailIndex = 0; trailIndex < trailCount; trailIndex++) {
            const ratio = (trailIndex + 1) / trailCount;
            const color = mixCssColors(endColor, startColor, ratio);
            const dx = parseInt(values.trailOffsetX) * ratio + "px";
            const dy = parseInt(values.trailOffsetY) * ratio + "px";
            shadows.push(`${dx} ${dy} ${color}`);
        }
    }
    if (json.shadowOffsetX || json.shadowOffsetY || json.shadowBlur || json.shadowColor) {
        shadows.push(
            `${values.shadowOffsetX} ${values.shadowOffsetY} ${values.shadowBlur} ${values.shadowColor}`
        );
    }
    if (shadows.length) {
        element.style.setProperty("text-shadow", shadows.join(", "));
    } else {
        element.style.removeProperty("text-shadow");
    }
    const transforms = [];
    if (json.rotate) {
        transforms.push(`rotate(${json.rotate})`);
    }
    if (json.skewX || json.skewY) {
        transforms.push(`skew(${values.skewX}, ${values.skewY})`);
    }
    if (json.tiltX || json.tiltY) {
        transforms.push(`perspective(${values.tiltPerspective}em)`);
        transforms.push(`rotateX(${values.tiltX})`);
        transforms.push(`rotateY(${values.tiltY})`);
    }
    if (json.moveX || json.moveY) {
        transforms.push(`translate(${values.moveX}, ${values.moveY})`);
    }
    if (json.scale) {
        transforms.push(`scale(${values.scale})`);
    }
    if (transforms.length) {
        element.style.setProperty("transform", transforms.join(" "));
        element.style.setProperty("display", "inline-block");
    } else {
        element.style.removeProperty("transform");
        element.style.removeProperty("display");
    }
    if (json.outline) {
        element.style.setProperty(
            "-webkit-text-stroke",
            `${values.outline} ${values.outlineColor}`
        );
        if (!shadows.length) {
            // Make Chrome draw outline on selected text.
            element.style.setProperty("text-shadow", "0 0 transparent");
        }
    } else {
        element.style.removeProperty("-webkit-text-stroke");
    }
}

export function getActualColor(color, doc) {
    if (color.startsWith("var(--")) {
        return getCSSVariableValue(color.substring(6, color.length - 1), getHtmlStyle(doc));
    }
    return color;
}

export const TextEffectUtil = {
    applyConfiguredEffects,
    defaults,
    getActualColor,
};
