import { Component, onWillUnmount, proxy, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

const WCAG_URL = "https://www.w3.org/WAI/WCAG22/Understanding/";

const TEXT_LABELS = {
    body: _t("Text color"),
    link: _t("Link color"),
    primary_button: _t("Primary button text (regular)"),
    primary_outline_button: _t("Primary outline button text (regular)"),
    secondary_button: _t("Secondary button text (regular)"),
    secondary_outline_button: _t("Secondary outline button text (regular)"),
    title: _t("Title color"),
};

const BUTTON_LABELS = {
    primary_button: {
        component: _t("Primary button color"),
        text: _t("Primary button text"),
    },
    primary_outline_button: {
        component: _t("Primary outline button color"),
        text: _t("Primary outline button text"),
    },
    secondary_button: {
        component: _t("Secondary button color"),
        text: _t("Secondary button text"),
    },
    secondary_outline_button: {
        component: _t("Secondary outline button color"),
        text: _t("Secondary outline button text"),
    },
};

const parseColor = (value) => {
    if (!value) {
        return null;
    }
    const hexadecimal = value.trim().match(/^#([\da-f]{3,8})$/i)?.[1];
    if (hexadecimal) {
        const expanded =
            hexadecimal.length === 3 || hexadecimal.length === 4
                ? [...hexadecimal].map((character) => character.repeat(2)).join("")
                : hexadecimal;
        return {
            red: parseInt(expanded.slice(0, 2), 16),
            green: parseInt(expanded.slice(2, 4), 16),
            blue: parseInt(expanded.slice(4, 6), 16),
            alpha: expanded.length === 8 ? parseInt(expanded.slice(6, 8), 16) / 255 : 1,
        };
    }
    const values = value.match(/[\d.]+/g)?.map(Number);
    if (!values || values.length < 3) {
        return null;
    }
    return {
        red: values[0],
        green: values[1],
        blue: values[2],
        alpha: values[3] ?? 1,
    };
};

const composite = (foreground, background) => {
    const alpha = foreground.alpha + background.alpha * (1 - foreground.alpha);
    const channel = (name) =>
        (foreground[name] * foreground.alpha +
            background[name] * background.alpha * (1 - foreground.alpha)) /
        alpha;
    return {
        red: channel("red"),
        green: channel("green"),
        blue: channel("blue"),
        alpha,
    };
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

const getLuminance = (color) => {
    const channelLuminance = (channel) => {
        channel /= 255;
        return channel <= 0.04045 ? channel / 12.92 : Math.pow((channel + 0.055) / 1.055, 2.4);
    };
    return (
        0.2126 * channelLuminance(color.red) +
        0.7152 * channelLuminance(color.green) +
        0.0722 * channelLuminance(color.blue)
    );
};

const getContrastRatio = (firstColor, secondColor) => {
    const firstLuminance = getLuminance(firstColor);
    const secondLuminance = getLuminance(secondColor);
    return (
        (Math.max(firstLuminance, secondLuminance) + 0.05) /
        (Math.min(firstLuminance, secondLuminance) + 0.05)
    );
};

const toHex = (color) =>
    `#${[color.red, color.green, color.blue]
        .map((channel) => Math.round(channel).toString(16).padStart(2, "0"))
        .join("")}`.toUpperCase();

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
    return candidates.sort((first, second) => first.amount - second.amount)[0].color;
};

const isLargeText = (element) => {
    const style = getElementStyle(element);
    const fontSize = parseFloat(style.fontSize);
    const fontWeight = parseInt(style.fontWeight, 10) || 400;
    return fontSize >= 24 || (fontSize >= 18.66 && fontWeight >= 700);
};

const getContrastIssue = ({
    background,
    foreground,
    label,
    preset,
    suggestionLabel,
    type,
    aaRequirement,
    aaaRequirement,
}) => {
    const ratio = getContrastRatio(foreground, background);
    if (ratio >= aaRequirement) {
        return null;
    }
    return {
        aaPass: false,
        aaRequirement,
        aaaPass: aaaRequirement ? ratio >= aaaRequirement : null,
        aaaRequirement,
        background: toHex(background),
        foreground: toHex(foreground),
        key: `${preset}-${type}-${label}-${toHex(foreground)}-${toHex(background)}`,
        label,
        preset,
        ratio: ratio.toFixed(2),
        suggestion: toHex(getAccessibleColor(foreground, background, aaRequirement)),
        suggestionLabel:
            suggestionLabel || (type === "text" ? _t("text color") : _t("button color")),
        type,
    };
};

const getButtonStateColors = (element, isHover) => {
    const style = getElementStyle(element);
    const adjacent = getBackgroundColor(element.parentElement);
    let background;
    let border;
    let focusIndicator;
    let text;
    if (isHover) {
        const backgroundColor = getButtonColor(style, "hover-bg");
        background = backgroundColor ? composite(backgroundColor, adjacent) : adjacent;
        const borderColor = getButtonColor(style, "hover-border-color");
        border = borderColor ? composite(borderColor, adjacent) : adjacent;
        const textColor = getButtonColor(style, "hover-color");
        text = composite(textColor || parseColor(style.color), background);
        const focusColor = getButtonColor(style, "focus-shadow-rgb");
        focusIndicator = focusColor ? composite({ ...focusColor, alpha: 0.5 }, adjacent) : adjacent;
    } else {
        background = getBackgroundColor(element);
        const borderColor = parseColor(style.borderTopColor);
        border = borderColor ? composite(borderColor, adjacent) : adjacent;
        const textColor = parseColor(style.color);
        text = textColor ? composite(textColor, background) : null;
    }
    const indicator =
        getContrastRatio(background, adjacent) >= getContrastRatio(border, adjacent)
            ? background
            : border;
    return { adjacent, background, focusIndicator, indicator, text };
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
        const suggestion = getAccessibleColor(foreground, surroundingText, 3);
        issues.push({
            criterion: "1.4.1",
            diagnosis: _t("The link has only %(ratio)s:1 contrast with surrounding text.", {
                ratio: ratio.toFixed(2),
            }),
            foreground: toHex(foreground),
            key: `${preset}-link-identification`,
            label: _t("Link color against surrounding text"),
            preset,
            ratio: ratio.toFixed(2),
            suggestion: toHex(suggestion),
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
        autoCheck: t.boolean().optional(false),
        close: t.function(),
        onIframeLoad: t.function(),
    });

    setup() {
        this.state = proxy({
            checkButtons: false,
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

    onButtonChecksChange(ev) {
        this.state.checkButtons = ev.target.checked;
        if (this.state.hasChecked) {
            this.checkAccessibility();
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
        const textSelector = this.state.checkButtons
            ? "[data-color-preset] [data-wcag-text]"
            : "[data-color-preset] [data-wcag-text]:not([data-wcag-button])";
        const elements = this.previewDocument.querySelectorAll(textSelector);
        for (const [index, element] of elements.entries()) {
            if (index && index % 5 === 0) {
                await new Promise((resolve) => setTimeout(resolve));
            }
            const background = getBackgroundColor(element);
            const declaredForeground = parseColor(getElementStyle(element).color);
            const foreground = composite(declaredForeground, background);
            const preset = element.closest("[data-color-preset]").dataset.colorPreset;
            const largeText = isLargeText(element);
            const issue = getContrastIssue({
                aaRequirement: largeText ? 3 : 4.5,
                aaaRequirement: largeText ? 4.5 : 7,
                background,
                foreground,
                label: TEXT_LABELS[element.dataset.wcagRole],
                preset,
                type: "text",
            });
            if (issue) {
                issues.push(issue);
            }
        }
        issues.push(...getLinkIdentificationIssues(this.previewDocument));

        const buttons = this.state.checkButtons
            ? this.previewDocument.querySelectorAll("[data-wcag-button]")
            : [];
        for (const button of buttons) {
            const preset = button.closest("[data-color-preset]").dataset.colorPreset;
            const labels = BUTTON_LABELS[button.dataset.wcagRole];
            const regular = getButtonStateColors(button, false);
            const hover = getButtonStateColors(button, true);
            const buttonTextIsLarge = isLargeText(button);
            const textRequirements = buttonTextIsLarge
                ? { aaRequirement: 3, aaaRequirement: 4.5 }
                : { aaRequirement: 4.5, aaaRequirement: 7 };
            const buttonIssues = [
                getContrastIssue({
                    ...textRequirements,
                    background: hover.background,
                    foreground: hover.text,
                    label: _t("%(button)s (hover/focus)", { button: labels.text }),
                    preset,
                    type: "text",
                }),
                getContrastIssue({
                    aaRequirement: 3,
                    aaaRequirement: null,
                    background: regular.adjacent,
                    foreground: regular.indicator,
                    label: _t("%(button)s (regular)", { button: labels.component }),
                    preset,
                    type: "nonText",
                }),
                getContrastIssue({
                    aaRequirement: 3,
                    aaaRequirement: null,
                    background: hover.adjacent,
                    foreground: hover.indicator,
                    label: _t("%(button)s (hover/focus)", { button: labels.component }),
                    preset,
                    type: "nonText",
                }),
                getContrastIssue({
                    aaRequirement: 3,
                    aaaRequirement: null,
                    background: hover.adjacent,
                    foreground: hover.focusIndicator,
                    label: _t("%(button)s focus indicator", { button: labels.component }),
                    preset,
                    suggestionLabel: _t("focus indicator color"),
                    type: "nonText",
                }),
            ];
            issues.push(...buttonIssues.filter(Boolean));
        }

        const failedPresets = new Set(issues.map((issue) => issue.preset));
        for (const preset of failedPresets) {
            this.previewDocument
                .querySelector(`[data-color-preset="${preset}"] [data-wcag-warning]`)
                .removeAttribute("hidden");
        }

        clearTimeout(this.loadingTimer);
        this.state.hasChecked = true;
        this.state.isChecking = false;
        this.state.issues = issues;
        this.state.showLoading = false;
    }
}
