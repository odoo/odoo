// The color functions below mirror the SCSS ones the color presets are
// compiled with (Bootstrap, web and html_editor), including libsass' numeric
// behavior (`mix()` rounds channels, HSL adjustments do not), so that a preview
// matches what is compiled on save.

const WHITE = { r: 255, g: 255, b: 255, a: 1 };
const BLACK = { r: 0, g: 0, b: 0, a: 1 };

/**
 * @param {string} cssColor hexadecimal or rgb()/rgba()
 * @returns {{r: number, g: number, b: number, a: number}|null}
 */
export function parseColor(cssColor) {
    cssColor = cssColor.trim();
    const hex = cssColor.match(/^#([0-9a-f]{3,8})$/i)?.[1];
    if (hex) {
        const digits = hex.length <= 4 ? [...hex].map((digit) => digit + digit) : hex.match(/../g);
        const [r, g, b, a = 255] = digits.map((digit) => parseInt(digit, 16));
        return { r, g, b, a: a / 255 };
    }
    const rgba = cssColor.match(/^rgba?\(([^)]+)\)$/)?.[1].split(/[\s,/]+/).map(parseFloat);
    if (rgba) {
        const [r, g, b, a = 1] = rgba;
        return { r, g, b, a };
    }
    return null;
}

export function formatColor({ r, g, b, a }) {
    const [red, green, blue] = [r, g, b].map(sassRound);
    return a >= 1 ? `rgb(${red}, ${green}, ${blue})` : `rgba(${red}, ${green}, ${blue}, ${a})`;
}

// libsass' round: half up, with its 5 digits precision tolerance.
function sassRound(value) {
    return value % 1 - 0.5 > -1e-6 ? Math.ceil(value) : Math.floor(value);
}

function mix(color1, color2, weight) {
    const p = weight / 100;
    const w = p * 2 - 1;
    const a = color1.a - color2.a;
    const w1 = ((w * a === -1 ? w : (w + a) / (1 + w * a)) + 1) / 2;
    const w2 = 1 - w1;
    return {
        r: sassRound(color1.r * w1 + color2.r * w2),
        g: sassRound(color1.g * w1 + color2.g * w2),
        b: sassRound(color1.b * w1 + color2.b * w2),
        a: color1.a * p + color2.a * (1 - p),
    };
}

const tintColor = (color, weight) => mix(WHITE, color, weight);
const shadeColor = (color, weight) => mix(BLACK, color, weight);
const opaque = (background, foreground) => mix({ ...foreground, a: 1 }, background, foreground.a * 100);

function toHsl({ r, g, b }) {
    [r, g, b] = [r / 255, g / 255, b / 255];
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const delta = max - min;
    const l = (max + min) / 2;
    let h = 0;
    let s = 0;
    if (Math.abs(max - min) > 1e-10) {
        s = l < 0.5 ? delta / (max + min) : delta / (2 - max - min);
        if (r === max) {
            h = (g - b) / delta + (g < b ? 6 : 0);
        } else if (g === max) {
            h = (b - r) / delta + 2;
        } else {
            h = (r - g) / delta + 4;
        }
    }
    return { h: h * 60, s: s * 100, l: l * 100 };
}

function fromHsl({ h, s, l }, a) {
    [h, s, l] = [h / 360, s / 100, l / 100];
    const m2 = l <= 0.5 ? l * (s + 1) : l + s - l * s;
    const m1 = l * 2 - m2;
    const hueToRgb = (hue) => {
        hue = ((hue % 1) + 1) % 1;
        if (hue * 6 < 1) {
            return m1 + (m2 - m1) * hue * 6;
        }
        if (hue * 2 < 1) {
            return m2;
        }
        if (hue * 3 < 2) {
            return m1 + (m2 - m1) * (2 / 3 - hue) * 6;
        }
        return m1;
    };
    return { r: hueToRgb(h + 1 / 3) * 255, g: hueToRgb(h) * 255, b: hueToRgb(h - 1 / 3) * 255, a };
}

function adjustLightness(color, amount) {
    const hsl = toHsl(color);
    return fromHsl({ ...hsl, l: Math.min(100, Math.max(0, hsl.l + amount)) }, color.a);
}

// Bootstrap's `luminance()`, whose table is `((v / 255 + .055) / 1.055) ^ 2.4`
// rounded to 4 digits, indexed by the (floored) channel value.
function luminance({ r, g, b }) {
    const channel = (value) =>
        value / 255 < 0.04045
            ? value / 255 / 12.92
            : Math.round(((Math.floor(value) / 255 + 0.055) / 1.055) ** 2.4 * 10000) / 10000;
    return channel(r) * 0.2126 + channel(g) * 0.7152 + channel(b) * 0.0722;
}

function contrastRatio(background, foreground) {
    const l1 = luminance(background);
    const l2 = luminance(opaque(background, foreground));
    return l1 > l2 ? (l1 + 0.05) / (l2 + 0.05) : (l2 + 0.05) / (l1 + 0.05);
}

// web's `color-contrast()` override.
function colorContrast(background, constants) {
    const realColor = opaque(constants.bodyBg, background);
    let maxRatio = 0;
    let maxRatioColor = null;
    for (const color of [constants.contrastLight, constants.contrastDark, WHITE, BLACK]) {
        const ratio = contrastRatio(realColor, color);
        if (ratio > constants.minContrastRatio) {
            return color;
        } else if (ratio > maxRatio) {
            maxRatio = ratio;
            maxRatioColor = color;
        }
    }
    return maxRatioColor;
}

const luma = ({ r, g, b }) => ((r * 0.299 + g * 0.587 + b * 0.114) / 255) * 100;

// html_editor's `has-enough-contrast()` and `increase-contrast()`.
function hasEnoughContrast(color1, color2) {
    return (
        Math.abs(color1.r - color2.r) + Math.abs(color1.g - color2.g) + Math.abs(color1.b - color2.b) >=
        500
    );
}

function increaseContrast(color1, color2) {
    const lightnessIncrement = luma(color1) < luma(color2) ? -1 : 1;
    let lightness = toHsl(color1).l;
    for (
        let i = 0;
        lightness > 0.1 && lightness < 99.9 && i < 25 && !hasEnoughContrast(color1, color2);
        i++
    ) {
        color1 = adjustLightness(color1, lightnessIncrement);
        lightness += lightnessIncrement;
    }
    return color1;
}

const toRgb = ({ r, g, b }) => [r, g, b].map((value) => Math.round(value * 1e5) / 1e5).join(", ");

// Bootstrap's `button-variant()` and `button-outline-variant()` colors.
function buttonVariant(background, border, constants) {
    const color = colorContrast(background, constants);
    const isLight = ["r", "g", "b", "a"].every((key) => color[key] === constants.contrastLight[key]);
    const hoverBackground = isLight ? shadeColor(background, 15) : tintColor(background, 15);
    const activeBackground = isLight ? shadeColor(background, 20) : tintColor(background, 20);
    return {
        color,
        bg: background,
        border,
        "hover-color": colorContrast(hoverBackground, constants),
        "hover-bg": hoverBackground,
        "hover-border": isLight ? shadeColor(border, 20) : tintColor(border, 10),
        "focus-rgb": toRgb(mix(color, border, 15)),
        "active-color": colorContrast(activeBackground, constants),
        "active-bg": activeBackground,
        "active-border": isLight ? shadeColor(border, 25) : tintColor(border, 10),
        "disabled-color": colorContrast(background, constants),
    };
}

/**
 * Computes the colors that the `.o_cc<index>` rules (html_editor) compile from
 * a color preset, as `--o-preview-o-cc<index>-*` values. A value the compiled
 * CSS does not declare is returned empty, to remove a previous one.
 *
 * @param {number} index
 * @param {Object<string, {r, g, b, a}|null>} preset the preset colors (`bg`,
 *        `text`, `headings`, `h2`… `h6`, `link`, `btn-primary`,
 *        `btn-primary-border`, `btn-secondary`, `btn-secondary-border`), null
 *        when not set
 * @param {Object} constants compiled values: `bodyBg`, `contrastLight`,
 *        `contrastDark`, `minContrastRatio`, `primary`, `secondary`
 * @returns {Object<string, string>}
 */
export function computeColorPresetPreview(index, preset, constants) {
    const values = {};
    const bg = preset.bg;
    // `o-bg-color()` with a 0 opacity threshold.
    const text = preset.text || (bg.a > 0 ? colorContrast(bg, constants) : null);
    values.bg = bg;
    if (text) {
        values.text = text;
    }
    if (text && bg.a > 0) {
        values["text-muted"] = { ...text, a: text.a * 0.7 };
    }
    for (const key of ["headings", "h2", "h3", "h4", "h5", "h6"]) {
        if (preset[key]) {
            values[key] = preset[key];
        }
    }
    const link = preset.link || constants.primary;
    values.link = increaseContrast(link, bg);
    values["link-hover"] = increaseContrast(adjustLightness(link, -15), bg);
    for (const type of ["primary", "secondary"]) {
        const btn = preset[`btn-${type}`];
        const btnColor = btn || constants[type];
        const borderColor = preset[`btn-${type}-border`] || btnColor;
        for (const [key, value] of Object.entries(buttonVariant(btnColor, borderColor, constants))) {
            values[`btn-${type}-${key}`] = value;
        }
        const outline = btn ? btnColor : increaseContrast(borderColor, bg);
        values[`btn-${type}-outline`] = outline;
        values[`btn-${type}-outline-contrast`] = colorContrast(outline, constants);
        values[`btn-${type}-outline-rgb`] = toRgb(outline);
    }
    if (index === 1) {
        // The body colors (website's `bootstrap_overridden.scss`).
        values["bg-rgb"] = toRgb(bg);
        if (text) {
            values["text-rgb"] = toRgb(text);
        }
        values["link-rgb"] = toRgb(values.link);
        const bodyLinkHover = increaseContrast(adjustLightness(values.link, -15), bg);
        values["body-link-hover"] = bodyLinkHover;
        values["body-link-hover-rgb"] = toRgb(bodyLinkHover);
    }
    for (const key of ["text", "text-muted", "text-rgb", "headings", "h2", "h3", "h4", "h5", "h6"]) {
        values[key] ??= "";
    }
    return Object.fromEntries(
        Object.entries(values).map(([key, value]) => [
            `o-cc${index}-${key}`,
            typeof value === "string" ? value : formatColor(value),
        ])
    );
}
