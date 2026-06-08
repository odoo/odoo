import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { hashCode } from "@web/core/utils/strings";

export const TEXT_EFFECT_PRESET_HASH = "presetHash";

export const defaults = {
    shadowColor: "rgba(0, 0, 0, 0.5)",
    shadowOffsetX: "2px",
    shadowOffsetY: "2px",
    shadowBlur: "3px",
    outline: "0px",
    outlineColor: "#808080",
};

export const shadowParams = ["shadowColor", "shadowOffsetX", "shadowOffsetY", "shadowBlur"];

function getShadowValues(shadow = {}) {
    return Object.fromEntries(
        shadowParams.map((paramName) => [paramName, shadow[paramName] || defaults[paramName]])
    );
}

export function isShadowParam(paramName) {
    return shadowParams.includes(paramName);
}

export function getShadowCount(textEffect) {
    return textEffect.shadows?.length || 0;
}

function getStableTextEffectCopy(value) {
    if (Array.isArray(value)) {
        return value.map((item) => getStableTextEffectCopy(item));
    }
    if (value && typeof value === "object") {
        return Object.fromEntries(
            Object.keys(value)
                .filter((key) => key !== TEXT_EFFECT_PRESET_HASH)
                .sort()
                .map((key) => [key, getStableTextEffectCopy(value[key])])
        );
    }
    return value;
}

export function getTextEffectPresetHash(textEffect) {
    return hashCode(JSON.stringify(getStableTextEffectCopy(textEffect)));
}

export function updateTextEffectPresetHash(textEffect) {
    if (textEffect.preset === "custom") {
        textEffect[TEXT_EFFECT_PRESET_HASH] = getTextEffectPresetHash(textEffect);
    } else {
        delete textEffect[TEXT_EFFECT_PRESET_HASH];
    }
}

export function getTextEffectPresetId(textEffect) {
    return textEffect.preset === "custom"
        ? textEffect[TEXT_EFFECT_PRESET_HASH] || getTextEffectPresetHash(textEffect)
        : textEffect.preset;
}

export function hasConfiguredTextEffect(textEffect) {
    return getShadowCount(textEffect) > 0 || parseFloat(textEffect.outline || "0") > 0;
}

export function getShadows(textEffect) {
    return (textEffect.shadows || []).map((shadow) => getShadowValues(shadow));
}

export function setShadowParam(textEffect, paramName, shadowIndex, value) {
    const shadows = getShadows(textEffect);
    while (shadows.length <= shadowIndex) {
        shadows.push(getShadowValues({}));
    }
    shadows[shadowIndex][paramName] = value;
    textEffect.shadows = shadows;
}

export function deleteShadowParam(textEffect, paramName, shadowIndex) {
    const shadows = getShadows(textEffect);
    if (shadows[shadowIndex]) {
        delete shadows[shadowIndex][paramName];
    }
    textEffect.shadows = shadows;
}

export function addShadow(textEffect) {
    const shadows = getShadows(textEffect);
    shadows.push(getShadowValues({}));
    textEffect.shadows = shadows;
}

export function removeShadow(textEffect, shadowIndex) {
    const shadows = getShadows(textEffect);
    if (!shadows.length) {
        return false;
    }
    if (shadows.length === 1) {
        delete textEffect.shadows;
        return true;
    }
    shadows.splice(shadowIndex, 1);
    textEffect.shadows = shadows;
    return true;
}

export function applyConfiguredEffects(element, previousTextEffect = {}) {
    let json = {};
    if (element.dataset.textEffect) {
        json = JSON.parse(element.dataset.textEffect);
    }
    if (
        Object.keys(previousTextEffect).length &&
        json.preset === "custom" &&
        Object.keys(json).filter((key) => key !== TEXT_EFFECT_PRESET_HASH).length === 1
    ) {
        json = Object.assign({}, previousTextEffect, json);
        element.dataset.textEffect = JSON.stringify(json);
    }
    const values = Object.assign({}, defaults, json);
    const shadows = getShadows(json).map(
        (shadow) =>
            `${shadow.shadowOffsetX} ${shadow.shadowOffsetY} ${shadow.shadowBlur} ${shadow.shadowColor}`
    );
    if (shadows.length) {
        element.style.setProperty("text-shadow", shadows.join(", "));
    } else {
        element.style.removeProperty("text-shadow");
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
