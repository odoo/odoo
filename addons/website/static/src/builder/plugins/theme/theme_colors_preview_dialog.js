import { Component, onWillUnmount, proxy, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { convertHslToRgb, convertRgbToHsl } from "@web/core/utils/colors";
import { composite, getContrastRatio, parseColor, toHex } from "@website/builder/color_contrast";

const WCAG_URL = "https://www.w3.org/WAI/WCAG22/Understanding/";

const TEXT_LABELS = {
    body: _t("Text"),
    link: _t("Link"),
    title: _t("Title"),
};

const BUTTON_LABELS = {
    primary_button: {
        component: _t("Primary button"),
        text: _t("Primary button text"),
    },
    primary_outline_button: {
        component: _t("Primary outline button"),
        text: _t("Primary outline button text"),
    },
    secondary_button: {
        component: _t("Secondary button"),
        text: _t("Secondary button text"),
    },
    secondary_outline_button: {
        component: _t("Secondary outline button"),
        text: _t("Secondary outline button text"),
    },
};

const STATUS_LABELS = {
    danger: _t("Error badge"),
    info: _t("Info badge"),
    success: _t("Success badge"),
    warning: _t("Warning badge"),
};

const getColorVariable = (preset, role) => {
    // The text color of a button cannot be set: it is computed from the
    // button color, which is the one to change.
    const suffixes = {
        body: "text",
        link: "link",
        primary_button: "btn-primary",
        primary_outline_button: "btn-primary",
        secondary_button: "btn-secondary",
        secondary_outline_button: "btn-secondary",
        title: "headings",
    };
    return suffixes[role] ? `o-cc${preset}-${suffixes[role]}` : null;
};

const getElementStyle = (element) => element.ownerDocument.defaultView.getComputedStyle(element);

const getButtonColor = (style, property) =>
    parseColor(
        style.getPropertyValue(`--btn-${property}`) ||
            style.getPropertyValue(`--bs-btn-${property}`)
    );

const getBackgroundColor = (element) => {
    const layers = [];
    for (let current = element; current; current = current.parentElement) {
        const color = parseColor(getElementStyle(current).backgroundColor);
        if (color?.alpha) {
            layers.push(color);
        }
    }
    return layers.reverse().reduce((background, foreground) => composite(foreground, background), {
        red: 255,
        green: 255,
        blue: 255,
        alpha: 1,
    });
};

const mix = (color, target, amount) => ({
    red: color.red + (target - color.red) * amount,
    green: color.green + (target - color.green) * amount,
    blue: color.blue + (target - color.blue) * amount,
    alpha: 1,
});

const getAccessibleColor = (foreground, background, minimumRatio) => {
    const candidates = [];
    for (const target of [0, 255]) {
        const targetColor = { red: target, green: target, blue: target, alpha: 1 };
        if (getContrastRatio(targetColor, background) < minimumRatio) {
            continue;
        }
        let lowerBound = 0;
        let upperBound = 1;
        for (let index = 0; index < 12; index++) {
            const amount = (lowerBound + upperBound) / 2;
            if (getContrastRatio(mix(foreground, target, amount), background) < minimumRatio) {
                lowerBound = amount;
            } else {
                upperBound = amount;
            }
        }
        const color = mix(foreground, target, upperBound);
        for (const channel of ["red", "green", "blue"]) {
            color[channel] = Math.round(color[channel]);
        }
        while (getContrastRatio(color, background) < minimumRatio) {
            for (const channel of ["red", "green", "blue"]) {
                color[channel] += Math.sign(target - color[channel]);
            }
        }
        candidates.push({ color, amount: upperBound });
    }
    // Neither black nor white may reach the ratio (e.g. 7:1 on a mid-tone).
    return candidates.sort((first, second) => first.amount - second.amount)[0]?.color || null;
};

const getAccessibleLinkColor = (foreground, background, surroundingText, minimumTextRatio) => {
    const requirements = [
        [background, minimumTextRatio],
        [surroundingText, 3],
    ];
    const isValid = (color) =>
        requirements.every(([reference, minimum]) => getContrastRatio(color, reference) >= minimum);
    const hsl = convertRgbToHsl(foreground.red, foreground.green, foreground.blue);
    let best = null;
    let bestLightnessDifference = Infinity;
    for (let index = 0; index <= 1000; index++) {
        const lightness = index / 10;
        const color = {
            ...convertHslToRgb(hsl.hue, hsl.saturation, lightness),
            alpha: 1,
        };
        const lightnessDifference = Math.abs(lightness - hsl.lightness);
        if (isValid(color) && lightnessDifference < bestLightnessDifference) {
            best = color;
            bestLightnessDifference = lightnessDifference;
        }
    }
    return best && toHex(best) !== toHex(foreground) ? best : null;
};

const isLargeText = (element) => {
    const style = getElementStyle(element);
    const fontSize = parseFloat(style.fontSize);
    const fontWeight = parseInt(style.fontWeight, 10) || 400;
    return fontSize >= 24 || (fontSize >= 18.66 && fontWeight >= 700);
};

const getContrastIssue = ({
    adjustBackground = false,
    background,
    foreground,
    label,
    preset,
    rule,
    state = _t("regular"),
    type,
    aaRequirement,
    aaaRequirement,
    colorType,
    colorVariable,
    suggestedColor,
}) => {
    const ratio = getContrastRatio(foreground, background);
    const targetRequirement = aaaRequirement || aaRequirement;
    if (ratio >= targetRequirement) {
        return null;
    }
    const getSuggestion = (requirement) =>
        adjustBackground
            ? getAccessibleColor(background, foreground, requirement)
            : getAccessibleColor(foreground, background, requirement);
    const suggestion =
        suggestedColor === undefined
            ? getSuggestion(targetRequirement) || getSuggestion(aaRequirement)
            : suggestedColor;
    return {
        aaPass: ratio >= aaRequirement,
        aaRequirement,
        aaaPass: aaaRequirement ? ratio >= aaaRequirement : null,
        aaaRequirement,
        background: toHex(background),
        colorType,
        colorVariable,
        criterion: type === "text" ? "1.4.3 / 1.4.6" : "1.4.11",
        // The color that the suggestion replaces
        currentColor: toHex(adjustBackground ? background : foreground),
        foreground: toHex(foreground),
        key: `${preset}-${type}-${label}-${state}-${toHex(foreground)}-${toHex(background)}`,
        label,
        preset,
        ratio: ratio.toFixed(2),
        rule,
        state,
        noJointLinkColor: suggestedColor === null,
        suggestion: suggestion && toHex(suggestion),
        type,
        url: `${WCAG_URL}${type === "text" ? "contrast-minimum" : "non-text-contrast"}`,
    };
};

const getButtonStateColors = (element, state) => {
    const style = getElementStyle(element);
    const adjacent = getBackgroundColor(element.parentElement);
    const propertyPrefix = state === "active" ? "active-" : state === "regular" ? "" : "hover-";
    const backgroundColor = getButtonColor(style, `${propertyPrefix}bg`);
    const background = backgroundColor
        ? composite(backgroundColor, adjacent)
        : getBackgroundColor(element);
    const textColor = getButtonColor(style, `${propertyPrefix}color`) || parseColor(style.color);
    const text = textColor ? composite(textColor, background) : null;
    return { background, text };
};

const getLinkIdentificationIssues = (document) => {
    const issues = [];
    for (const link of document.querySelectorAll("[data-wcag-role='link']")) {
        const style = getElementStyle(link);
        if (style.textDecorationLine.includes("underline")) {
            continue;
        }
        const background = getBackgroundColor(link);
        const foreground = composite(parseColor(style.color), background);
        const surroundingText = composite(
            parseColor(getElementStyle(link.parentElement).color),
            background
        );
        const ratio = getContrastRatio(foreground, surroundingText);
        if (ratio >= 3) {
            continue;
        }
        const preset = link.closest("[data-color-preset]").dataset.colorPreset;
        const suggestion = getAccessibleLinkColor(foreground, background, surroundingText, 4.5);
        issues.push({
            aaPass: false,
            aaRequirement: 3,
            aaaPass: null,
            aaaRequirement: null,
            background: toHex(surroundingText),
            colorVariable: `o-cc${preset}-link`,
            criterion: "1.4.1",
            currentColor: toHex(foreground),
            diagnosis: _t("The link has only %(ratio)s:1 contrast with surrounding text.", {
                ratio: ratio.toFixed(2),
            }),
            foreground: toHex(foreground),
            key: `${preset}-link-identification`,
            label: _t("Link"),
            preset,
            ratio: ratio.toFixed(2),
            rule: _t("Link contrast with surrounding text"),
            state: _t("regular"),
            noJointLinkColor: !suggestion,
            suggestion: suggestion ? toHex(suggestion) : null,
            surroundingText: toHex(surroundingText),
            type: "linkIdentification",
            url: `${WCAG_URL}use-of-color`,
        });
    }
    return issues;
};

export class ThemeColorsPreviewDialog extends Component {
    static template = "website.ThemeColorsPreviewDialog";
    static components = { Dialog };
    props = useProps({
        applyColor: t.function().optional(),
        autoCheck: t.boolean().optional(false),
        close: t.function(),
        onIframeLoad: t.function(),
    });

    setup() {
        this.state = proxy({
            applyingKey: null,
            hasChecked: false,
            isChecking: false,
            isPreviewReady: false,
            issues: [],
            selectedPreset: null,
            showInfo: false,
            showLoading: false,
        });
        onWillUnmount(() => clearTimeout(this.loadingTimer));
    }

    onIframeLoad(previewDocument) {
        this.previewDocument = previewDocument;
        for (const filter of previewDocument.querySelectorAll("[data-wcag-preset-filter]")) {
            const isActive = filter.dataset.preset === this.state.selectedPreset;
            filter.classList.toggle("active", isActive);
            filter.setAttribute("aria-pressed", isActive.toString());
            filter.addEventListener("click", () => this.togglePresetFilter(filter.dataset.preset));
        }
        this.state.isPreviewReady = true;
        this.props.onIframeLoad(previewDocument);
        if (this.props.autoCheck) {
            this.checkAccessibility();
        }
    }

    get displayedIssues() {
        if (!this.state.selectedPreset) {
            return this.state.issues;
        }
        return this.state.issues.filter((issue) => issue.preset === this.state.selectedPreset);
    }

    togglePresetFilter(preset = null) {
        this.state.selectedPreset = this.state.selectedPreset === preset ? null : preset;
        this.state.showInfo = false;
        for (const filter of this.previewDocument.querySelectorAll("[data-wcag-preset-filter]")) {
            const isActive = filter.dataset.preset === this.state.selectedPreset;
            filter.classList.toggle("active", isActive);
            filter.setAttribute("aria-pressed", isActive.toString());
        }
    }

    toggleInfo() {
        this.state.showInfo = !this.state.showInfo;
    }

    async applySuggestion(issue) {
        this.state.applyingKey = issue.key;
        try {
            await this.props.applyColor(
                { colorType: issue.colorType, mainParam: issue.colorVariable },
                issue.suggestion
            );
            await this.checkAccessibility();
        } finally {
            this.state.applyingKey = null;
        }
    }

    async checkAccessibility() {
        this.state.hasChecked = false;
        this.state.isChecking = true;
        this.state.issues = [];
        this.state.showInfo = false;
        this.state.showLoading = false;
        this.loadingTimer = setTimeout(() => (this.state.showLoading = true), 2000);

        const issues = [];
        for (const warning of this.previewDocument.querySelectorAll("[data-wcag-warning]")) {
            warning.hidden = true;
        }
        const elements = this.previewDocument.querySelectorAll(
            "[data-color-preset] [data-wcag-text]:not([data-wcag-button])"
        );
        for (const [index, element] of elements.entries()) {
            if (index && index % 5 === 0) {
                await new Promise((resolve) => setTimeout(resolve));
            }
            const background = getBackgroundColor(element);
            const declaredForeground = parseColor(getElementStyle(element).color);
            const foreground = composite(declaredForeground, background);
            const preset = element.closest("[data-color-preset]").dataset.colorPreset;
            const largeText = isLargeText(element);
            const aaRequirement = largeText ? 3 : 4.5;
            const aaaRequirement = largeText ? 4.5 : 7;
            let suggestedColor;
            if (
                element.dataset.wcagRole === "link" &&
                !getElementStyle(element).textDecorationLine.includes("underline")
            ) {
                const surroundingText = composite(
                    parseColor(getElementStyle(element.parentElement).color),
                    background
                );
                suggestedColor =
                    getAccessibleLinkColor(
                        foreground,
                        background,
                        surroundingText,
                        aaaRequirement
                    ) ||
                    getAccessibleLinkColor(foreground, background, surroundingText, aaRequirement);
            }
            const issue = getContrastIssue({
                aaRequirement,
                aaaRequirement,
                background,
                colorVariable: getColorVariable(preset, element.dataset.wcagRole),
                foreground,
                label: TEXT_LABELS[element.dataset.wcagRole],
                preset,
                rule: _t("Text contrast with background"),
                suggestedColor,
                type: "text",
            });
            if (issue) {
                issues.push(issue);
            }
        }
        issues.push(...getLinkIdentificationIssues(this.previewDocument));

        const buttons = this.previewDocument.querySelectorAll("[data-wcag-button]");
        for (const button of buttons) {
            const preset = button.closest("[data-color-preset]").dataset.colorPreset;
            const labels = BUTTON_LABELS[button.dataset.wcagRole];
            const buttonTextIsLarge = isLargeText(button);
            const textRequirements = buttonTextIsLarge
                ? { aaRequirement: 3, aaaRequirement: 4.5 }
                : { aaRequirement: 4.5, aaaRequirement: 7 };
            const states = [
                ["regular", _t("regular")],
                ["hover", _t("hover")],
                ["focus", _t("focus")],
                ["active", _t("active")],
            ];
            const isOutline = button.dataset.wcagRole.endsWith("_outline_button");
            for (const [state, stateLabel] of states) {
                const colors = getButtonStateColors(button, state);
                const textIssue = getContrastIssue({
                    ...textRequirements,
                    // The button color is the text of a regular outline
                    // button and the background of the other buttons.
                    adjustBackground: !isOutline || state !== "regular",
                    background: colors.background,
                    colorVariable: getColorVariable(preset, button.dataset.wcagRole),
                    foreground: colors.text,
                    label: labels.text,
                    preset,
                    rule: _t("Text contrast with button background"),
                    state: stateLabel,
                    type: "text",
                });
                if (textIssue) {
                    issues.push(textIssue);
                }
            }
        }

        // The text of a badge is its status color, over a light tint of it.
        for (const badge of this.previewDocument.querySelectorAll("[data-wcag-status]")) {
            const background = getBackgroundColor(badge);
            const largeText = isLargeText(badge);
            const issue = getContrastIssue({
                aaRequirement: largeText ? 3 : 4.5,
                aaaRequirement: largeText ? 4.5 : 7,
                background,
                colorType: "theme",
                colorVariable: badge.dataset.wcagStatus,
                foreground: composite(parseColor(getElementStyle(badge).color), background),
                label: STATUS_LABELS[badge.dataset.wcagStatus],
                preset: null,
                rule: _t("Text contrast with badge background"),
                type: "text",
            });
            if (issue) {
                issues.push(issue);
            }
        }

        const failedPresets = new Set(issues.map((issue) => issue.preset));
        for (const preset of failedPresets) {
            const container = preset
                ? `[data-color-preset="${preset}"]`
                : "[data-wcag-status-colors]";
            this.previewDocument
                .querySelector(`${container} [data-wcag-warning]`)
                .removeAttribute("hidden");
        }

        clearTimeout(this.loadingTimer);
        this.state.hasChecked = true;
        this.state.isChecking = false;
        this.state.issues = issues;
        this.state.showLoading = false;
    }
}
