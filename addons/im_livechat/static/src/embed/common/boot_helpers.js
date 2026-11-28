import { url } from "@web/core/utils/urls";
import { session } from "@web/session";

import {
    capBrightness,
    getBubbleColors,
    getContrastColor,
    MAX_BRIGHTNESS_FOR_WHITE_CONTRAST,
} from "@im_livechat/embed/common/color_utils";

// OKLCH lightness and maximum chroma of the bubbles of each role. The visitor's bubbles
// are darker than the operator's, so the two stay apart even with close colors.
const BUBBLE_STYLES = {
    primary: { lightness: 0.87, maxChroma: 0.06 },
    secondary: { lightness: 0.95, maxChroma: 0.04 },
};

/**
 * CSS vars derived from a single configured color (primary or secondary).
 *
 * @param {string} color
 * @param {"primary"|"secondary"} role
 */
function getColorCssVariables(color, role) {
    const { lightness, maxChroma } = BUBBLE_STYLES[role];
    const bubble = getBubbleColors(color, lightness, maxChroma);
    return {
        [`--o-mail-livechat-${role}`]: color,
        [`--o-mail-livechat-${role}-text`]: getContrastColor(color),
        [`--o-mail-livechat-${role}-outline`]: capBrightness(
            color,
            MAX_BRIGHTNESS_FOR_WHITE_CONTRAST
        ),
        [`--o-mail-livechat-${role}-bubble-bg`]: bubble.background,
        [`--o-mail-livechat-${role}-bubble-border`]: bubble.border,
    };
}

async function loadFont(name, url, targetDocument) {
    await targetDocument.fonts.ready;
    if ([...targetDocument.fonts].some(({ family }) => family === name)) {
        // Font already loaded.
        return;
    }
    const link = document.createElement("link");
    link.rel = "preload";
    link.as = "font";
    link.href = url;
    link.crossOrigin = "";
    const style = document.createElement("style");
    style.appendChild(
        document.createTextNode(`
            @font-face {
                font-family: ${name};
                src: url('${url}') format('woff2');
                font-weight: normal;
                font-style: normal;
                font-display: block;
            }
        `)
    );
    const loadPromise = new Promise((res, rej) => {
        link.addEventListener("load", res);
        link.addEventListener("error", rej);
    });
    targetDocument.head.appendChild(link);
    targetDocument.head.appendChild(style);
    return loadPromise;
}

function loadStyle(target) {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = url("/im_livechat/assets_embed.css");
    const stylesLoadedPromise = new Promise((res, rej) => {
        link.addEventListener("load", res);
        link.addEventListener("error", rej);
    });
    target.appendChild(link);
    return stylesLoadedPromise;
}

/**
 * @param {HTMLElement} target
 * @returns {HTMLDivElement}
 */
export function makeRoot(target) {
    const root = document.createElement("div");
    root.classList.add("o-livechat-root");
    root.setAttribute("id", `o-livechat-root-${luxon.DateTime.now().ts + Math.random()}`);
    root.style.zIndex = "calc(9e999)";
    root.style.position = "relative";
    root.style.display = "block";
    const options = session.livechatData?.options ?? {};
    const cssVariables = {
        ...getColorCssVariables(options.primary_color, "primary"),
        ...getColorCssVariables(options.secondary_color, "secondary"),
    };
    for (const [name, value] of Object.entries(cssVariables)) {
        root.style.setProperty(name, value);
    }
    target.appendChild(root);
    return root;
}

export async function loadAssets(styleTarget) {
    const document = styleTarget.ownerDocument;
    await Promise.all([
        loadStyle(styleTarget),
        loadFont(
            "Material Symbols Outlined",
            url("/im_livechat/material_symbols_outlined"),
            document
        ),
        loadFont("odoo_ui_icons", url("/im_livechat/odoo_ui_icons"), document),
    ]);
}

/**
 * Initialize the livechat container by loading the styles and
 * the fonts.
 *
 * @param {HTMLElement} root
 * @returns {Promise<ShadowRoot>}
 */
export async function makeShadow(root) {
    const shadow = root.attachShadow({ mode: "open" });
    await loadAssets(shadow);
    return shadow;
}
