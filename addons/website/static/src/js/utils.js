/** @odoo-module native */
import { urlFunctions } from "@html_editor/utils/url";
import { App, Component } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { getTemplate } from "@web/core/templates";
import { _t, appTranslateFn } from "@web/core/translation";
import { patch } from "@web/core/utils/patch";
import { UrlAutoComplete } from "@website/components/autocomplete_with_pages/url_autocomplete";

const log = makeLogger("website.utils.wutils");

/**
 * @param {string} url
 * @param {Node} body
 * @returns {Deferred<string[]>}
 */
export function loadAnchors(url, body) {
    const endAnchors = log.perf("loadAnchors", () => ({ url }));
    return new Promise(function (resolve, reject) {
        if (url === window.location.pathname || url[0] === "#") {
            log.logic("loadAnchors: current page", () => ({ url, hasBody: !!body }));
            resolve(body ? body.outerHTML : document.body.outerHTML);
        } else if (url.length && !url.startsWith("http")) {
            log.logic("loadAnchors: fetching internal page", () => ({ url }));
            fetch(window.location.origin + url)
                .then((response) => response.text())
                .then((text) => {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(text, "text/html");
                    return doc.body;
                })
                .then(resolve, reject);
        } else {
            log.logic("loadAnchors: external or empty url, no anchors fetched", () => ({
                url,
            }));
            resolve();
        }
    })
        .then(function (response) {
            const fragment = new DOMParser().parseFromString(response, "text/html");
            const anchorEls = fragment.querySelectorAll(
                `[id][data-anchor="true"], .modal[id][data-display="onClick"]`,
            );
            const anchors = Array.from(anchorEls).map((el) => "#" + el.id);

            if (!anchors.includes("#top")) {
                anchors.unshift("#top");
            }
            if (!anchors.includes("#bottom")) {
                anchors.push("#bottom");
            }
            endAnchors({ anchors: anchors.length });
            return anchors;
        })
        .catch((error) => {
            log.logic("loadAnchors: failed, fall back to []", () => ({
                url,
                error: error?.message,
            }));
            // eslint-disable-next-line no-console -- non-fatal fetch error, quiet debug diagnostic (falls back to [])
            console.debug(error);
            return [];
        });
}

/**
 * @param {HTMLInputElement} input
 */
export function autocompleteWithPages(input, options = {}, env = undefined) {
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
    container.classList.add(
        "ui-widget",
        "ui-autocomplete",
        "ui-widget-content",
        "border-0",
    );
    document.body.appendChild(container);
    owlApp.mount(container);
    log.lifecycle("autocompleteWithPages mounted", () => ({
        input: input?.name || input?.id,
    }));
    return () => {
        log.lifecycle("autocompleteWithPages destroyed", () => ({
            input: input?.name || input?.id,
        }));
        owlApp.destroy();
        container.remove();
    };
}

export function sendRequest(route, params) {
    function _addInput(form, name, value) {
        const param = document.createElement("input");
        param.setAttribute("type", "hidden");
        param.setAttribute("name", name);
        param.setAttribute("value", value);
        form.appendChild(param);
    }

    const form = document.createElement("form");
    form.setAttribute("action", route);
    form.setAttribute("method", params.method || "POST");
    if (params.forceTopWindow) {
        form.setAttribute("target", "_top");
    }

    if (odoo.csrf_token) {
        _addInput(form, "csrf_token", odoo.csrf_token);
    }

    for (const key in params) {
        const value = params[key];
        if (Array.isArray(value) && value.length) {
            for (const val of value) {
                _addInput(form, key, val);
            }
        } else {
            _addInput(form, key, value);
        }
    }

    log.pipeline("sendRequest: submitting form", () => ({
        route,
        method: form.getAttribute("method"),
        forceTopWindow: !!params.forceTopWindow,
        inputs: form.elements.length,
    }));
    document.body.appendChild(form);
    form.submit();
}

/**
 * @param {string|HTMLImageElement} src
 * @returns {Promise<string>}
 */
export async function svgToPNG(src) {
    return _exportToPNG(src, "svg+xml");
}

/**
 * @param {string|HTMLImageElement} src
 * @returns {Promise<string>}
 */
export async function webpToPNG(src) {
    return _exportToPNG(src, "webp");
}

/**
 * @private
 * @param {string|HTMLImageElement} src
 * @param {string} format
 * @returns {Promise<string>}
 */
async function _exportToPNG(src, format) {
    function checkImg(imgEl) {
        return imgEl.naturalHeight !== 0;
    }
    function toPNGViaCanvas(imgEl) {
        const canvas = document.createElement("canvas");
        canvas.width = imgEl.width;
        canvas.height = imgEl.height;
        canvas.getContext("2d").drawImage(imgEl, 0, 0);
        return canvas.toDataURL("image/png");
    }

    if (src instanceof HTMLImageElement) {
        const loadedImgEl = src;
        if (checkImg(loadedImgEl)) {
            log.logic(
                "_exportToPNG: image already loaded, direct canvas export",
                () => ({
                    format,
                }),
            );
            return toPNGViaCanvas(loadedImgEl);
        }
        src = loadedImgEl.src;
    }

    const endExport = log.perf("_exportToPNG load image", () => ({ format }));
    return new Promise((resolve) => {
        const imgEl = new Image();
        imgEl.onload = () => {
            if (format !== "svg+xml" || checkImg(imgEl)) {
                resolve(imgEl);
                return;
            }
            log.logic(
                "_exportToPNG: svg without intrinsic size, refetch and resize",
                () => ({
                    src: imgEl.src.slice(0, 120),
                }),
            );

            imgEl.height = 1000;
            imgEl.style.opacity = 0;
            document.body.appendChild(imgEl);

            const request = new XMLHttpRequest();
            request.open("GET", imgEl.src, true);
            request.onload = () => {
                const parser = new DOMParser();
                const result = parser.parseFromString(request.responseText, "text/xml");
                const svgEl = result.getElementsByTagName("svg")[0];

                svgEl.setAttribute("width", imgEl.width);
                svgEl.setAttribute("height", imgEl.height);
                imgEl.remove();

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
    }).then((loadedImgEl) => {
        endExport(() => ({
            width: loadedImgEl.width,
            height: loadedImgEl.height,
        }));
        return toPNGViaCanvas(loadedImgEl);
    });
}

/**
 * @returns {HTMLIframeElement}
 */
export function generateGMapIframe() {
    const iframeEl = document.createElement("iframe");
    iframeEl.classList.add("s_map_embedded", "o_not_editable");
    iframeEl.setAttribute("width", "100%");
    iframeEl.setAttribute("height", "100%");
    iframeEl.setAttribute("frameborder", "0");
    iframeEl.setAttribute("scrolling", "no");
    iframeEl.setAttribute("marginheight", "0");
    iframeEl.setAttribute("marginwidth", "0");
    iframeEl.setAttribute("src", "about:blank");
    iframeEl.setAttribute("aria-label", _t("Map"));
    return iframeEl;
}

/**
 * @param {DOMStringMap} dataset
 * @returns {string}
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
 * @param {Object} self
 * @returns {boolean}
 */
export function isMobile(self) {
    let isMobile;
    self.trigger_up("service_context_get", {
        callback: (ctx) => {
            isMobile = ctx["isMobile"];
        },
    });

    return isMobile;
}

/**
 * @param {string} formId
 * @param {HTMLElement} parentEl
 * @returns {Object|undefined}
 */
export function getParsedDataFor(formId, parentEl) {
    const dataForEl = parentEl.querySelector(`[data-for='${formId}']`);
    if (!dataForEl) {
        log.logic("getParsedDataFor: no data-for element", () => ({ formId }));
        return;
    }
    return JSON.parse(
        dataForEl.dataset.values
            .replace(/([,:[]\s*)True/g, "$1true")
            .replace(/([,:[]\s*)(False|None)/g, '$1""')
            .replace(/'(\s*[,:\]}])/g, '"$1')
            .replace(/([{[:,]\s*)'/g, '$1"'),
    );
}

/**
 * @param {DocumentFragment|HTMLElement|String} content
 * @param {Boolean} [keepScripts=false]
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
    log.pipeline("cloneContentEls", () => ({
        fromString: typeof content === "string",
        children: copyFragment.childElementCount,
        scripts: copyFragment.querySelectorAll("script").length,
        keepScripts,
    }));
    if (!keepScripts) {
        copyFragment
            .querySelectorAll("script")
            .forEach((scriptEl) => scriptEl.remove());
    }
    return copyFragment;
}

/**
 * @param {Object} seo_data
 * @param {Component} OptimizeSEODialog
 * @param {Object} services
 */
export function checkAndNotifySEO(seo_data, OptimizeSEODialog, services) {
    if (seo_data) {
        let message;
        if (!seo_data.website_meta_title) {
            message = _t("Page title not set.");
        } else if (!seo_data.website_meta_description) {
            message = _t("Page description not set.");
        }
        log.logic("checkAndNotifySEO", () => ({
            hasTitle: !!seo_data.website_meta_title,
            hasDescription: !!seo_data.website_meta_description,
            notify: !!message,
        }));
        if (message) {
            const closeNotification = services.notification.add(message, {
                type: "warning",
                sticky: false,
                buttons: [
                    {
                        name: _t("Optimize SEO"),
                        onClick: () => {
                            log.lifecycle("checkAndNotifySEO: open OptimizeSEODialog");
                            services.dialog.add(OptimizeSEODialog);
                            closeNotification();
                        },
                    },
                ],
            });
        }
    }
}

/**
 * @param {string} value
 * @returns {string}
 */
export function slugify(value) {
    return !value
        ? ""
        : value
              .trim()
              .normalize("NFKD")
              .toLowerCase()
              .replace(/['’]/g, "-")
              .replace(/\s+/g, "-")
              .replace(/[^\w-]+/g, "")
              .replace(/--+/g, "-");
}

patch(urlFunctions, {
    isAbsoluteURLInCurrentDomain(url, env = null) {
        const res = super.isAbsoluteURLInCurrentDomain(url, env);
        if (res) {
            return true;
        }

        const w = env?.services.website.currentWebsite;
        if (!w) {
            return false;
        }

        let origin;
        try {
            origin = new URL(url, window.location.origin).origin;
        } catch {
            return false;
        }
        return `${origin}/`.startsWith(w.domain);
    },
});
