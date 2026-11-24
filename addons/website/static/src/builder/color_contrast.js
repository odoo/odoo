/**
 * Helpers to measure the WCAG contrast of colors, given as
 * `{ red, green, blue, alpha }` objects (channels from 0 to 255, alpha from 0
 * to 1).
 */

export function parseColor(value) {
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
}

/**
 * @returns the color seen when `foreground` is drawn over `background`
 */
export function composite(foreground, background) {
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
}

function getLuminance(color) {
    const channelLuminance = (channel) => {
        channel /= 255;
        return channel <= 0.04045 ? channel / 12.92 : Math.pow((channel + 0.055) / 1.055, 2.4);
    };
    return (
        0.2126 * channelLuminance(color.red) +
        0.7152 * channelLuminance(color.green) +
        0.0722 * channelLuminance(color.blue)
    );
}

export function getContrastRatio(firstColor, secondColor) {
    const firstLuminance = getLuminance(firstColor);
    const secondLuminance = getLuminance(secondColor);
    return (
        (Math.max(firstLuminance, secondLuminance) + 0.05) /
        (Math.min(firstLuminance, secondLuminance) + 0.05)
    );
}

export function toHex(color) {
    return `#${[color.red, color.green, color.blue]
        .map((channel) => Math.round(channel).toString(16).padStart(2, "0"))
        .join("")}`.toUpperCase();
}
