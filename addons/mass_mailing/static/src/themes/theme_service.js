import { children } from "@html_editor/utils/dom_traversal";
import { parseHTML } from "@html_editor/utils/html";
import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";
import { Reactive } from "@web/core/utils/reactive";
import { renderToMarkup } from "@web/core/utils/render";

function hasDataOption(element, attribute) {
    attribute = "data-" + attribute;
    return element.hasAttribute(attribute) && element.getAttribute(attribute) !== "false";
}

function getClassName(name) {
    return name ? "o_" + name + "_theme" : "";
}

function getNameFromClass(className) {
    const match = className.match(/^o_(.*)_theme$/);
    return match ? match[1] : undefined;
}

export class ThemeModel extends Reactive {
    constructor(services) {
        super();
        this.orm = services.orm;
        this.loadedAssets = new Set();
        this.loadedThemes = new Map();
        this.loadingPromise = new Deferred();
    }

    computeThemesTemplates(themesEl) {
        for (const theme of children(themesEl)) {
            this.preProcessImages(theme);
            const themeOptions = {
                className: getClassName(theme.dataset.name),
                hideFromMobile: hasDataOption(theme, "hide-from-mobile"),
                html: markup(theme.innerHTML.trim()),
                imgPath: theme.dataset.img || "",
                layoutStyles: theme.dataset.layoutStyles || "",
                name: theme.dataset.name,
                nowrap: hasDataOption(theme, "nowrap"),
                title: theme.getAttribute("title") || "",
            };
            if (hasDataOption(theme, "images-info")) {
                const imagesInfo = Object.assign(
                    { all: {} },
                    JSON.parse(theme.dataset.imagesInfo || "{}")
                );
                for (const [key, info] of Object.entries(imagesInfo)) {
                    imagesInfo[key] = Object.assign(
                        {
                            module: "mass_mailing",
                            format: "jpg",
                        },
                        imagesInfo.all,
                        info
                    );
                }
                themeOptions.getImageInfo = (filename) => imagesInfo[filename] || imagesInfo.all;
            }
            // Wrap the Theme `html` with a technical layout.
            themeOptions.html = renderToMarkup("mass_mailing.ThemeLayout", themeOptions);
            this.loadedThemes.set(themeOptions.name, themeOptions);
        }
    }

    preProcessImages(theme) {
        const images = theme.querySelectorAll("img[src]");
        for (const image of images) {
            if (!image.dataset.originalSrc) {
                image.dataset.originalSrc = image.getAttribute("src");
            }
        }
    }

    getThemeName(classList) {
        const themeClass = [...classList].find(getNameFromClass);
        return themeClass && getNameFromClass(themeClass);
    }

    getThemes() {
        return this.loadedThemes;
    }

    async load(asset = "mass_mailing.email_designer_themes") {
        if (!this.loadedAssets.has(asset)) {
            const themesHTML = await this.orm.silent.call(
                "ir.ui.view",
                "render_public_asset",
                [asset, {}],
                {}
            );
            this.computeThemesTemplates(parseHTML(document, themesHTML));
            this.loadedAssets.add(asset);
            this.loadingPromise.resolve();
        }
        return this.loadingPromise;
    }
}

registry.category("services").add("mass_mailing.themes", {
    dependencies: ["orm"],

    start(env, { orm }) {
        const services = { orm };
        return new ThemeModel(services);
    },
});
