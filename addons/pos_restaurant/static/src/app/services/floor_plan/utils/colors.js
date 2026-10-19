const COLORS = {
    black: [20, 20, 20],
    green: [60, 160, 90],
    blue: [30, 130, 210],
    red: [220, 80, 90],
    orange: [250, 170, 60],
    yellow: [245, 205, 80],
    purple: [150, 100, 220],
    grey: [120, 130, 140],
    lightGrey: [200, 205, 210],
    turquoise: [40, 180, 200],
    white: [249, 250, 251],
};

function getColorSet() {
    return COLORS;
}

export function getColors() {
    return Object.keys(getColorSet()).map((k) => ({
        key: k,
        value: getColorRGBA(k),
    }));
}

function parseHexColor(value) {
    if (!value.startsWith("#")) {
        return null;
    }
    let hex = value.slice(1);
    if (hex.length === 3) {
        hex =
            hex
                .split("")
                .map((c) => c + c)
                .join("") + "ff";
    } else if (hex.length === 4) {
        hex = hex
            .split("")
            .map((c) => c + c)
            .join("");
    } else if (hex.length === 6) {
        hex = hex + "ff";
    }
    if (hex.length !== 8) {
        return null;
    }

    const r = parseInt(hex.slice(0, 2), 16);
    const g = parseInt(hex.slice(2, 4), 16);
    const b = parseInt(hex.slice(4, 6), 16);
    const a = parseInt(hex.slice(6, 8), 16) / 255;
    return [r, g, b, a];
}

function parseRgb(value) {
    const rgbMatch = value.match(/rgba?\s*\(\s*([^)]+)\)/);
    if (rgbMatch) {
        const parts = rgbMatch[1].split(",").map((s) => s.trim());
        const r = parseInt(parts[0], 10);
        const g = parseInt(parts[1], 10);
        const b = parseInt(parts[2], 10);
        const a = parts[3] !== undefined ? parseFloat(parts[3]) : 1;
        return [r, g, b, a];
    }
    return null;
}

const colorCache = new Map();
const contrastCache = new Map();

export function getColorRGBA(value = "black", alpha = 1) {
    const rgb = getRgbArray(value);
    return `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${alpha})`;
}

export function getColorInfo(value, alpha = 1) {
    const rgb = getRgbArray(value);
    const [r, g, b] = rgb;
    let isDark;
    if (!contrastCache.has(value)) {
        isDark = isColorDark(r, g, b);
        contrastCache.set(value, isDark);
    } else {
        isDark = contrastCache.get(value);
    }
    return {
        rgb: `rgb(${r},${g},${b})`,
        rgba: `rgba(${r},${g},${b},${alpha})`,
        isDark,
    };
}

function getRgbArray(value) {
    value = value.trim();
    const colorSet = getColorSet();
    let rgb = colorSet[value];
    if (!rgb) {
        value = value.toLowerCase();
        if (colorCache.has(value)) {
            rgb = colorCache.get(value);
        } else {
            rgb = parseHexColor(value) || parseRgb(value);
            if (!rgb) {
                rgb = colorSet["black"];
            }
            colorCache.set(value, rgb);
        }
    }
    return rgb;
}

function isColorDark(r, g, b) {
    return (r * 299 + g * 587 + b * 114) / 1000 <= 64;
}
