export function insertKioskStyle(primaryBgColor) {
    const style = document.createElement("style");
    style.textContent = generateKioskCSS(primaryBgColor);
    document.head.appendChild(style);
}

function generateKioskCSS(companyPrimaryColor) {
    let bgPrimary = companyPrimaryColor;
    if (!bgPrimary || bgPrimary === "#875A7B") {
        bgPrimary = "#714B67";
    }
    const luminance = getLuminance(bgPrimary);
    const isLightBackground = luminance > 0.55;
    const shadedPrimary = shadeColor(bgPrimary, 0.6);

    const textBgPrimary = isLightBackground
        ? shadeColor(bgPrimary, 0.95)
        : mixColors("#FFFFFF", bgPrimary, 0.95);
    const primaryTextBorder = isLightBackground ? shadedPrimary : bgPrimary;

    const buttonActiveColor = shadeColor(bgPrimary, 0.2);

    return `
        :root {
            --primary-rgb: ${hexToRgb(bgPrimary)};
            --primary: ${bgPrimary};
        }

        .btn-primary {
            --btn-color: ${textBgPrimary};
            --btn-bg: ${bgPrimary};
            --btn-border-color: ${bgPrimary};
            --btn-hover-color: ${textBgPrimary};
            --btn-hover-bg: ${bgPrimary};
            --btn-hover-border-color: ${bgPrimary};
            --btn-focus-shadow-rgb: ${hexToRgb(mixColors(textBgPrimary, bgPrimary, 0.15))};
            --btn-active-color: ${textBgPrimary};
            --btn-active-bg: ${buttonActiveColor};
            --btn-active-border-color: ${buttonActiveColor};
            --btn-active-shadow: 0;
            --btn-disabled-color: ${textBgPrimary};
            --btn-disabled-bg: ${bgPrimary};
            --btn-disabled-border-color: ${bgPrimary};
        }

        .text-primary {
            --color: rgba(${hexToRgb(primaryTextBorder)}, var(--text-opacity, 1));
        }

        .border-primary {
            border-color: ${primaryTextBorder} !important;
        }

        .text-bg-primary :is(h1, h2, h3, h4, h5, h6) {
            color: ${textBgPrimary};
        }
      
        .text-bg-primary .btn-link, .badge.text-bg-primary, .btn.text-bg-primary {
            color: ${textBgPrimary} !important;
        }

        .text-bg-primary .btn-link:hover {
            color: ${mixColors(textBgPrimary, bgPrimary, 0.85)} !important;
        }

        .o_self_background {
            background-color: ${mixColors("#ffffff", bgPrimary, 0.85)};
        }
    `;
}

// Utilities

function getLuminance(hex) {
    const fullHex = expandHex(hex);
    const [r, g, b] = [0, 2, 4].map((i) => parseInt(fullHex.slice(i, i + 2), 16));
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255;
}

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
