export function insertKioskStyle(primaryBgColor, primaryTextColor) {
    const style = document.createElement("style");
    style.textContent = generateKioskCSS(primaryBgColor, primaryTextColor);
    document.head.appendChild(style);
}

function generateKioskCSS(primaryBg, primaryText = "#fff") {
    if (!primaryBg || primaryBg === "#875A7B") {
        primaryBg = "#714B67";
    }
    const activeBG = shadeColor(primaryBg, 0.2);
    const primaryRGB = hexToRgb(primaryBg);
    const hoverFocusRGB = hexToRgb(mixColors(primaryText, primaryBg, 0.15));
    const kioskBG = mixColors("#fff", primaryBg, 0.85);

    return `
:root {
  --primary-rgb: ${primaryRGB};
  --primary: ${primaryBg};
}

.btn-primary {
  --btn-color: ${primaryText};
  --btn-bg: ${primaryBg};
  --btn-border-color: ${primaryBg};
  --btn-hover-color: ${primaryText};
  --btn-hover-bg: ${primaryBg};
  --btn-hover-border-color: ${primaryBg};
  --btn-focus-shadow-rgb: ${hoverFocusRGB};
  --btn-active-color: ${primaryText};
  --btn-active-bg: ${activeBG};
  --btn-active-border-color: ${activeBG};
  --btn-active-shadow: 0;
  --btn-disabled-color: ${primaryText};
  --btn-disabled-bg: ${primaryBg};
  --btn-disabled-border-color: ${primaryBg};
}

.text-primary {
  --color: rgba(${primaryRGB}, var(--text-opacity, 1));
}

.o_kiosk_background {
  background-color: ${kioskBG};
}`;
}

// Utilities

function hexToRgb(hex) {
    const fullHex = expandHex(hex);
    const [r, g, b] = [0, 2, 4].map((i) => parseInt(fullHex.slice(i, i + 2), 16));
    return `${r}, ${g}, ${b}`;
}

/**
 * Blends two hex colors based on a given weight.
 *
 * @param {string} color1 - First hex color (e.g., "#ff0000" or "#f00").
 * @param {string} color2 - Second hex color (e.g., "#00ff00" or "#0f0").
 * @param {number} weight - Blend weight for the first color (range: 0 to 1).
 * @returns {string} - The resulting blended hex color (e.g., "#808000").
 */
function mixColors(color1, color2, weight) {
    const c1 = expandHex(color1);
    const c2 = expandHex(color2);
    let result = "#";

    for (let i = 0; i < 3; i++) {
        const comp1 = parseInt(c1.slice(i * 2, i * 2 + 2), 16);
        const comp2 = parseInt(c2.slice(i * 2, i * 2 + 2), 16);
        const mixed = Math.round(comp1 * weight + comp2 * (1 - weight));
        result += mixed.toString(16).padStart(2, "0");
    }

    return result;
}

//  Mix a color with black
function shadeColor(color, weight) {
    return mixColors("#000000", color, weight);
}

function expandHex(hex) {
    hex = hex.replace("#", "").trim();
    return hex.length === 3
        ? hex
              .split("")
              .map((c) => c + c)
              .join("")
        : hex.padEnd(6, "0");
}
