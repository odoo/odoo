/** @odoo-module */

import { serverUrl } from "@im_livechat/livechat_data";

async function loadFontAwesome() {
    await document.fonts.ready;
    if ([...document.fonts.values()].some(({ family }) => family === "FontAwesome")) {
        // FontAwesome already loaded.
        return;
    }
    const link = document.createElement("link");
    link.rel = "preload";
    link.as = "font";
    link.href = `${serverUrl}/im_livechat/font-awesome`;
    link.crossOrigin = "";
    const style = document.createElement("style");
    style.appendChild(
        document.createTextNode(`
            @font-face {
                font-family: 'FontAwesome';
                src: url('${serverUrl}/im_livechat/font-awesome') format('woff2');
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
    document.head.appendChild(link);
    document.head.appendChild(style);
    return loadPromise;
}

/**
 * @returns {HTMLDivElement}
 */
export function createRootNode() {
    const root = document.createElement("div");
    root.classList.add("o_livechat_root");
    document.body.appendChild(root);
    return root;
}

/**
 * Initialize the livechat container by loading the styles and
 * FontAwesome.
 *
 * @param {ShadowRoot} root
 */
export async function initializeLivechatContainer(root) {
    const stylesLink = document.createElement("link");
    stylesLink.rel = "stylesheet";
    stylesLink.href = `${serverUrl}/im_livechat/assets_embed.css`;
    const stylesLoadedPromise = new Promise((res, rej) => {
        stylesLink.addEventListener("load", res);
        stylesLink.addEventListener("error", rej);
    });
    const shadow = root.attachShadow({ mode: "open" });
    shadow.appendChild(stylesLink);
    await Promise.all([stylesLoadedPromise, loadFontAwesome()]);
    return shadow;
}
