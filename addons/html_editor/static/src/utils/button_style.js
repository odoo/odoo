import { _t } from "@web/core/l10n/translation";

/**
 * Return the default color options for the editor.
 *
 * Each option is an object with:
 *  - type      : identifier of the role (e.g., "link", "primary").
 *  - label     : UI label shown in the editor.
 *  - className : optional CSS classes for preview elements.
 *  - style     : optional inline style for preview elements.
 */
export const BUTTON_TYPES = [
    {
        type: "link",
        label: _t("Link"),
        style: "color: #008f8c;",
    },
    {
        type: "primary",
        label: _t("Button Primary"),
        className: "btn btn-sm btn-primary",
    },
    {
        type: "secondary",
        label: _t("Button Secondary"),
        className: "btn btn-sm btn-secondary",
    },
    {
        type: "custom",
        label: _t("Custom"),
    },
    // Note: by compatibility the dialog should be able to remove old
    // colors that were suggested like the BS status colors or the
    // alpha -> epsilon classes. This is currently done by removing
    // all btn-* classes anyway.
];

export const BUTTON_SHAPES = [
    { shape: "", label: "Default" },
    { shape: "rounded-circle", label: "Default + Rounded" },
    { shape: "outline", label: "Outline" },
    { shape: "outline rounded-circle", label: "Outline + Rounded" },
    { shape: "fill", label: "Fill" },
    { shape: "fill rounded-circle", label: "Fill + Rounded" },
    { shape: "flat", label: "Flat" },
];

export const BUTTON_SIZES = [
    { size: "sm", label: _t("Small") },
    { size: "", label: _t("Medium") },
    { size: "lg", label: _t("Large") },
];

export function computeButtonClasses(el, { type, size, shape }) {
    const classes = [...el.classList].filter(
        (value) => !value.match(/^(btn.*|rounded-circle|flat|(text|bg)-(o-color-\d$|\d{3}$))$/)
    );

    if (!type || type === "link") {
        return classes.filter(Boolean).join(" ");
    }

    classes.push("btn");
    if (size) {
        classes.push(`btn-${size}`);
    }

    let shapePrefix = "";
    if (shape) {
        const shapeValues = shape.split(" ");
        if (["outline", "fill"].includes(shapeValues[0])) {
            shapePrefix = `${shapeValues[0]}-`;
            classes.push(...shapeValues.slice(1));
        } else {
            classes.push(...shapeValues);
        }
    }

    classes.push(`btn-${shapePrefix}${type}`);

    return classes.filter(Boolean).join(" ");
}

export function getButtonType(el) {
    if (el.classList.contains("btn")) {
        const match = el.className.match(/btn(-[a-z0-9_-]*)(primary|secondary|custom)/);
        return match?.pop() || "link";
    }
    return "link";
}

export function getButtonSize(el) {
    return el.className.match(/btn-(sm|lg)/)?.[1] || "";
}

export function getButtonShape(el) {
    const shapeToRegex = (shape) => {
        const parts = shape.trim().split(/\s+/);
        const regexParts = parts.map((cls) => {
            if (["outline", "fill"].includes(cls)) {
                cls = `btn-${cls}`;
            }
            return `(?=.*\\b${cls}\\b)`;
        });
        return { regex: new RegExp(regexParts.join("")), nbParts: parts.length };
    };
    // If multiple shapes match, prefer the one with more specificity.
    let shapeMatched = "";
    let matchScore = 0;
    for (const { shape } of BUTTON_SHAPES) {
        if (!shape) {
            continue;
        }
        const { regex, nbParts } = shapeToRegex(shape);
        if (regex.test(el.className)) {
            if (matchScore < nbParts) {
                matchScore = nbParts;
                shapeMatched = shape;
            }
        }
    }
    return shapeMatched;
}
