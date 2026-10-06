const OVERLAY_ATTRIBUTE = "data-page-accessibility-overlay";

const parseColor = (value) => {
    const values = value?.match(/[\d.]+/g)?.map(Number);
    return values?.length >= 3
        ? { red: values[0], green: values[1], blue: values[2], alpha: values[3] ?? 1 }
        : null;
};

const composite = (foreground, background) => ({
    red: foreground.red * foreground.alpha + background.red * (1 - foreground.alpha),
    green: foreground.green * foreground.alpha + background.green * (1 - foreground.alpha),
    blue: foreground.blue * foreground.alpha + background.blue * (1 - foreground.alpha),
    alpha: 1,
});

const luminance = (color) => {
    const channel = (value) => {
        value /= 255;
        return value <= 0.04045 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4);
    };
    return (
        0.2126 * channel(color.red) + 0.7152 * channel(color.green) + 0.0722 * channel(color.blue)
    );
};

const contrast = (first, second) => {
    const firstLuminance = luminance(first);
    const secondLuminance = luminance(second);
    return (
        (Math.max(firstLuminance, secondLuminance) + 0.05) /
        (Math.min(firstLuminance, secondLuminance) + 0.05)
    );
};

const getBackground = (element) => {
    const window = element.ownerDocument.defaultView;
    const colors = [];
    for (let current = element; current; current = current.parentElement) {
        const style = window.getComputedStyle(current);
        if (style.backgroundImage !== "none") {
            return null;
        }
        const color = parseColor(style.backgroundColor);
        if (color?.alpha) {
            colors.push(color);
        }
    }
    return colors.reverse().reduce((background, foreground) => composite(foreground, background), {
        red: 255,
        green: 255,
        blue: 255,
        alpha: 1,
    });
};

const getTextNodes = (element) =>
    [...element.childNodes].filter((node) => node.nodeType === 3 && node.textContent.trim());

const hasContrastIssue = (element) => {
    const window = element.ownerDocument.defaultView;
    const style = window.getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    if (
        !rect.width ||
        !rect.height ||
        style.display === "none" ||
        style.visibility === "hidden" ||
        parseFloat(style.opacity) === 0
    ) {
        return false;
    }
    const background = getBackground(element);
    const foreground = parseColor(style.color);
    if (!background || !foreground) {
        return false;
    }
    const fontSize = parseFloat(style.fontSize);
    const fontWeight = parseInt(style.fontWeight, 10) || 400;
    const minimum = fontSize >= 24 || (fontSize >= 18.66 && fontWeight >= 700) ? 3 : 4.5;
    return contrast(composite(foreground, background), background) < minimum;
};

const addTextNodeOverlays = (document, textNodes) => {
    for (const textNode of textNodes) {
        const range = document.createRange();
        range.selectNodeContents(textNode);
        for (const rect of range.getClientRects()) {
            if (!rect.width || !rect.height) {
                continue;
            }
            const overlay = document.createElement("div");
            overlay.setAttribute(OVERLAY_ATTRIBUTE, "");
            overlay.style.cssText = `
                position: absolute;
                top: ${rect.top + document.defaultView.scrollY}px;
                left: ${rect.left + document.defaultView.scrollX}px;
                width: ${rect.width}px;
                height: ${rect.height}px;
                border: 2px solid #dc3545;
                box-shadow: 0 0 0 1px white;
                pointer-events: none;
                z-index: 2147483646;
            `;
            document.body.appendChild(overlay);
        }
        range.detach();
    }
};

export function clearPageAccessibilityHighlights(document) {
    for (const overlay of document.querySelectorAll(`[${OVERLAY_ATTRIBUTE}]`)) {
        overlay.remove();
    }
}

export function highlightPageTextContrastIssues(document) {
    clearPageAccessibilityHighlights(document);
    const root = document.querySelector("#wrapwrap") || document.body;
    let issueCount = 0;
    for (const element of root.querySelectorAll("*")) {
        if (element.matches("script, style, template, noscript")) {
            continue;
        }
        const textNodes = getTextNodes(element);
        if (textNodes.length && hasContrastIssue(element)) {
            addTextNodeOverlays(document, textNodes);
            issueCount++;
        }
    }
    return issueCount;
}
