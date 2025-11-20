import { appTranslateFn } from "@web/core/l10n/translation";
import { App, Component } from "@odoo/owl";
import { getTemplate } from "@web/core/templates";
import { UrlAutoComplete } from "@website/components/autocomplete_with_pages/url_autocomplete";
import * as urlUtils from "@html_editor/utils/url";
import { patch } from "@web/core/utils/patch";

/**
 * Allows to load anchors from a page.
 *
 * @param {string} url
 * @param {Node} body the editable for which to recover anchors
 * @returns {Deferred<string[]>}
 */
function loadAnchors(url, body) {
    return new Promise(function (resolve, reject) {
        if (url === window.location.pathname || url[0] === "#") {
            resolve(body ? body.outerHTML : document.body.outerHTML);
        } else if (url.length && !url.startsWith("http")) {
            // TODO: Might be broken with ReplaceMedia (NBY) and LinkTools
            fetch(window.location.origin + url)
                .then((response) => response.text())
                .then((text) => {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(text, "text/html");
                    return doc.body;
                })
                .then(resolve, reject);
        } else {
            // avoid useless query
            resolve();
        }
    })
        .then(function (response) {
            const fragment = new DOMParser().parseFromString(response, "text/html");
            const anchorEls = fragment.querySelectorAll(
                `[id][data-anchor="true"], .modal[id][data-display="onClick"]`
            );
            const anchors = Array.from(anchorEls).map((el) => "#" + el.id);

            // Always suggest the top and the bottom of the page as internal link
            // anchor even if the header and the footer are not in the DOM. Indeed,
            // the "scrollTo" function handles the scroll towards those elements
            // even when they are not in the DOM.
            if (!anchors.includes("#top")) {
                anchors.unshift("#top");
            }
            if (!anchors.includes("#bottom")) {
                anchors.push("#bottom");
            }
            return anchors;
        })
        .catch((error) => {
            console.debug(error);
            return [];
        });
}

/**
 * Allows the given input to propose existing website URLs.
 *
 * @param {HTMLInputElement} input
 */
function autocompleteWithPages(input, options = {}, env = undefined) {
    const owlApp = new App(UrlAutoComplete, {
        env: env || Component.env,
        dev: env ? env.debug : Component.env.debug,
        getTemplate,
        props: {
            options,
            loadAnchors,
            targetDropdown: input,
        },
        translatableAttributes: ["data-tooltip"],
        translateFn: appTranslateFn,
    });

    const container = document.createElement("div");
    container.classList.add("ui-widget", "ui-autocomplete", "ui-widget-content", "border-0");
    document.body.appendChild(container);
    owlApp.mount(container);
    return () => {
        owlApp.destroy();
        container.remove();
    };
}

/**
 * Converts a base64 SVG into a base64 PNG.
 *
 * @param {string|HTMLImageElement} src - an URL to a SVG or a *loaded* image
 *      with such an URL. This allows the call to potentially be a bit more
 *      efficient in that second case.
 * @returns {Promise<string>} a base64 PNG (as result of a Promise)
 */
export async function svgToPNG(src) {
    return _exportToPNG(src, "svg+xml");
}

/**
 * Converts a base64 WEBP into a base64 PNG.
 *
 * @param {string|HTMLImageElement} src - an URL to a WEBP or a *loaded* image
 *     with such an URL. This allows the call to potentially be a bit more
 *     efficient in that second case.
 * @returns {Promise<string>} a base64 PNG (as result of a Promise)
 */
export async function webpToPNG(src) {
    return _exportToPNG(src, "webp");
}

/**
 * Converts a formatted base64 image into a base64 PNG.
 *
 * @private
 * @param {string|HTMLImageElement} src - an URL to a image or a *loaded* image
 *     with such an URL. This allows the call to potentially be a bit more
 *     efficient in that second case.
 * @param {string} format - the format of the image
 * @returns {Promise<string>} a base64 PNG (as result of a Promise)
 */
async function _exportToPNG(src, format) {
    function checkImg(imgEl) {
        // Firefox does not support drawing SVG to canvas unless it has width
        // and height attributes set on the root <svg>.
        return imgEl.naturalHeight !== 0;
    }
    function toPNGViaCanvas(imgEl) {
        const canvas = document.createElement("canvas");
        canvas.width = imgEl.width;
        canvas.height = imgEl.height;
        canvas.getContext("2d").drawImage(imgEl, 0, 0);
        return canvas.toDataURL("image/png");
    }

    // In case we receive a loaded image and that this image is not problematic,
    // we can convert it to PNG directly.
    if (src instanceof HTMLImageElement) {
        const loadedImgEl = src;
        if (checkImg(loadedImgEl)) {
            return toPNGViaCanvas(loadedImgEl);
        }
        src = loadedImgEl.src;
    }

    // At this point, we either did not receive a loaded image or the received
    // loaded image is problematic => we have to do some asynchronous code.
    return new Promise((resolve) => {
        const imgEl = new Image();
        imgEl.onload = () => {
            if (format !== "svg+xml" || checkImg(imgEl)) {
                resolve(imgEl);
                return;
            }

            // Set arbitrary height on image and attach it to the DOM to force
            // width computation.
            imgEl.height = 1000;
            imgEl.style.opacity = 0;
            document.body.appendChild(imgEl);

            const request = new XMLHttpRequest();
            request.open("GET", imgEl.src, true);
            request.onload = () => {
                // Convert the data URI to a SVG element
                const parser = new DOMParser();
                const result = parser.parseFromString(request.responseText, "text/xml");
                const svgEl = result.getElementsByTagName("svg")[0];

                // Add the attributes Firefox needs and remove the image from
                // the DOM.
                svgEl.setAttribute("width", imgEl.width);
                svgEl.setAttribute("height", imgEl.height);
                imgEl.remove();

                // Convert the SVG element to a data URI
                const svg64 = btoa(new XMLSerializer().serializeToString(svgEl));
                const finalImg = new Image();
                finalImg.onload = () => {
                    resolve(finalImg);
                };
                finalImg.src = `data:image/svg+xml;base64,${svg64}`;
            };
            request.send();
        };
        imgEl.src = src;
    }).then((loadedImgEl) => toPNGViaCanvas(loadedImgEl));
}

/**
 * Generates a Google Maps URL based on the given parameter.
 *
 * @param {DOMStringMap} dataset
 * @returns {string} a Google Maps URL
 */
export function generateGMapLink(dataset) {
    return (
        "https://maps.google.com/maps?q=" +
        encodeURIComponent(dataset.mapAddress) +
        "&t=" +
        encodeURIComponent(dataset.mapType) +
        "&z=" +
        encodeURIComponent(dataset.mapZoom) +
        "&ie=UTF8&iwloc=&output=embed"
    );
}

/**
 * Returns the parsed data coming from the data-for element for the given form.
 *
 * @param {string} formId
 * @param {HTMLElement} parentEl
 * @returns {Object|undefined} the parsed data
 */
export function getParsedDataFor(formId, parentEl) {
    const dataForEl = parentEl.querySelector(`[data-for='${formId}']`);
    if (!dataForEl) {
        return;
    }
    return JSON.parse(
        dataForEl.dataset.values
            // replaces `True` by `true` if they are after `,` or `:` or `[`
            .replace(/([,:[]\s*)True/g, "$1true")
            // replaces `False` and `None` by `""` if they are after `,` or `:` or `[`
            .replace(/([,:[]\s*)(False|None)/g, '$1""')
            // replaces the `'` by `"` if they are before `,` or `:` or `]` or `}`
            .replace(/'(\s*[,:\]}])/g, '"$1')
            // replaces the `'` by `"` if they are after `{` or `[` or `,` or `:`
            .replace(/([{[:,]\s*)'/g, '$1"')
    );
}

/**
 * Deep clones children or parses a string into elements, with or without
 * <script> elements.
 *
 * @param {DocumentFragment|HTMLElement|String} content
 * @param {Boolean} [keepScripts=false] - whether to keep script tags or not.
 * @returns {DocumentFragment}
 */
export function cloneContentEls(content, keepScripts = false) {
    let copyFragment;
    if (typeof content === "string") {
        copyFragment = new Range().createContextualFragment(content);
    } else {
        copyFragment = new DocumentFragment();
        const els = [...content.children].map((el) => el.cloneNode(true));
        copyFragment.append(...els);
    }
    if (!keepScripts) {
        copyFragment.querySelectorAll("script").forEach((scriptEl) => scriptEl.remove());
    }
    return copyFragment;
}

/**
 * Converts a string into a URL-friendly slug.
 *
 * @param {string} value - The string to slugify.
 * @returns {string} The slugified string.
 */
export function slugify(value) {
    // `NFKD` as in `http_routing` python `slugify()`
    return !value
        ? ""
        : value
              .trim()
              .normalize("NFKD")
              .toLowerCase()
              .replace(/['’]/g, "-") // Replace apostrophes with hyphens
              .replace(/\s+/g, "-") // Replace spaces with -
              .replace(/[^\w-]+/g, "") // Remove all non-word chars
              .replace(/--+/g, "-"); // Replace multiple - with single -
}

patch(urlUtils, {
    isAbsoluteURLInCurrentDomain(url, env = null) {
        const res = super.isAbsoluteURLInCurrentDomain(url, env);
        if (res) {
            return true;
        }

        const w = env?.services.website.currentWebsite;
        if (!w) {
            return false;
        }

        // Make sure that while being on abc.odoo.com, if you edit a link and
        // enter an absolute URL using your real domain, it is still considered
        // to be added as relative, preferably.
        // In the past, you could not edit your website from abc.odoo.com if you
        // properly configured your real domain already.
        let origin;
        try {
            // Needed: "http:" would crash
            origin = new URL(url, window.location.origin).origin;
        } catch {
            return false;
        }
        return `${origin}/`.startsWith(w.domain);
    },
});

export default {
    loadAnchors: loadAnchors,
    autocompleteWithPages: autocompleteWithPages,
    svgToPNG: svgToPNG,
    webpToPNG: webpToPNG,
    generateGMapLink: generateGMapLink,
    slugify: slugify,
};
