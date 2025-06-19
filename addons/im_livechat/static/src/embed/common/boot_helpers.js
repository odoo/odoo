import { url } from "@web/core/utils/urls";

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
    target.appendChild(root);
    return root;
}

export async function loadAssets(styleTarget) {
    const document = styleTarget.ownerDocument;
    await Promise.all([
        loadStyle(styleTarget),
        loadFont("FontAwesome", url("/im_livechat/font-awesome"), document),
        loadFont("odoo_ui_icons", url("/im_livechat/odoo_ui_icons"), document),
    ]);
}

/**
 * Initialize the livechat container by loading the styles and
 * the fonts.
 *
 * @param {HTMLElement} root
 * @returns {ShadowRoot}
 */
export async function makeShadow(root) {
    const shadow = root.attachShadow({ mode: "open" });
    await loadAssets(shadow);
    return shadow;
}
