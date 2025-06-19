import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { SNIPPET_SPECIFIC_AFTER } from "@html_builder/utils/option_sequence";

export class CarouselSlidesOptionPlugin extends Plugin {
    static id = "carouselSlidesOption";

    resources = {
        builder_options: [
            withSequence(SNIPPET_SPECIFIC_AFTER, {
                template: "website.CarouselSlidesOption",
                selector:
                    ".s_carousel .carousel-item, .s_quotes_carousel .carousel-item, .s_carousel_intro .carousel-item, .s_carousel_cards .carousel-item",
            }),
        ],
        builder_actions: this.getActions(),
    };

    getActions() {
        return {
            setSlideLink: {
                preview: false,
                apply: ({ editingElement }) => {
                    const linkEl = editingElement.querySelector("a.slide-link");
                    if (linkEl) {
                        linkEl.parentElement.remove();
                    } else {
                        const wrapperEl = document.createElement("div");
                        wrapperEl.className = "slide-link-wrapper position-absolute top-0 start-0  d-block w-100 h-100 z-3 o_not_editable";
                        wrapperEl.setAttribute("contenteditable", "false");

                        const anchorEl = document.createElement("a");
                        anchorEl.className = "slide-link d-block w-100 h-100";
                        anchorEl.setAttribute("contenteditable", "true");

                        wrapperEl.appendChild(anchorEl);
                        editingElement.prepend(wrapperEl);
                    }
                },
                isApplied: ({ editingElement }) => {
                    const linkEl = editingElement.querySelector("a.slide-link");
                    return linkEl ? true : false;
                },
            },
            setSlideUrl: {
                preview: false,
                apply: ({ editingElement, value }) => {
                    const linkEl = editingElement.querySelector("a.slide-link");
                    let url = value;
                    if (!url) {
                        // As long as there is no URL, the image is not considered a link.
                        linkEl.removeAttribute("href");
                        return;
                    }
                    if (
                        !url.startsWith("/") &&
                        !url.startsWith("#") &&
                        !/^([a-zA-Z]*.):.+$/gm.test(url)
                    ) {
                        // We permit every protocol (http:, https:, ftp:, mailto:,...).
                        // If none is explicitly specified, we assume it is a http.
                        url = "http://" + url;
                    }
                    linkEl.setAttribute("href", url);
                },
                getValue: ({ editingElement }) => {
                    const linkEl = editingElement.querySelector("a.slide-link");
                    return linkEl?.getAttribute("href") || "";
                },
            },
        };
    }
}

registry.category("website-plugins").add(CarouselSlidesOptionPlugin.id, CarouselSlidesOptionPlugin);
