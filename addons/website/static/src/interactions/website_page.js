/** @odoo-module native */
import { browser } from "@web/core/browser/browser";
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { initZoomOdoo } from "@website/libs/zoomodoo/zoomodoo";

const log = makeLogger("website.interaction.website_page");

export class WebsitePage extends Interaction {
    static selector = "#wrapwrap";

    start() {
        this.addListener(document.body, "click", (ev) => {
            const langEl = ev.target.closest(".js_change_lang");
            if (langEl) {
                return this._onLangChangeClick(ev, langEl);
            }
            const publishEl = ev.target.closest(
                ".js_publish_management .js_publish_btn",
            );
            if (publishEl) {
                return this._onPublishBtnClick(ev, publishEl);
            }
        });
        this.addListener(document.body, "shown.bs.modal", (ev) => {
            ev.target.classList.add("modal_shown");
        });

        const endZoom = log.perf("WebsitePage start: init zoomable images");
        for (const imgEl of document.body.querySelectorAll(
            ".zoomable img[data-zoom]",
        )) {
            initZoomOdoo(imgEl);
        }
        endZoom(() => ({
            images: document.body.querySelectorAll(".zoomable img[data-zoom]").length,
        }));
    }

    /**
     * @param {MouseEvent} ev
     * @param {HTMLElement} target
     */
    _onLangChangeClick(ev, target) {
        ev.preventDefault();
        if (document.body.classList.contains("editor_enable")) {
            log.logic("WebsitePage lang change: ignored in editor", () => ({
                lang: target.dataset.url_code,
            }));
            return;
        }
        const redirect = {
            lang: encodeURIComponent(target.dataset.url_code),
            url: encodeURIComponent(
                target.getAttribute("href").replace(/[&?]edit_translations[^&?]+/, ""),
            ),
            hash: encodeURIComponent(browser.location.hash),
        };
        log.pipeline("WebsitePage lang change: redirect", () => ({ redirect }));
        browser.location.href = `/website/lang/${redirect.lang}?r=${redirect.url}${redirect.hash}`;
    }

    /**
     * @param {MouseEvent} ev
     * @param {HTMLElement} target
     */
    _onPublishBtnClick(ev, target) {
        ev.preventDefault();
        if (document.body.classList.contains("editor_enable")) {
            log.logic("WebsitePage publish button: ignored in editor");
            return;
        }

        const publishEl = target.closest(".js_publish_management");
        const endPublish = log.perf("WebsitePage website_publish_button", () => ({
            model: publishEl.dataset.object,
            id: publishEl.dataset.id,
        }));
        this.services.orm
            .call(publishEl.dataset.object, "website_publish_button", [
                [parseInt(publishEl.dataset.id, 10)],
            ])
            .then(function (result) {
                endPublish({ published: result });
                publishEl.classList.toggle("css_published", result);
                publishEl.classList.toggle("css_unpublished", !result);
                const itemEl = publishEl.closest("[data-publish]");
                if (itemEl) {
                    itemEl.dataset.publish = result ? "on" : "off";
                }
            });
    }
}

registry.category("public.interactions").add("website.website_page", WebsitePage);
