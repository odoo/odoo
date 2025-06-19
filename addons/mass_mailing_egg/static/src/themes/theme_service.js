import { children } from "@html_editor/utils/dom_traversal";
import { parseHTML } from "@html_editor/utils/html";
import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Reactive } from "@web/core/utils/reactive";
import { renderToString } from "@web/core/utils/render";

const DEFAULT_ASSET = "mass_mailing.email_designer_themes";

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
    }

    computeThemesTemplates(asset, themesEl) {
        // TODO EGGMAIL: do we have to use database records for themes? Why not
        // use assets? Do users have to be able to modify their DB to add templates?
        for (const theme of children(themesEl)) {
            const themeOptions = {
                className: getClassName(theme.dataset.name),
                hideFromMobile: hasDataOption(theme, "hide-from-mobile"),
                html: markup(theme.innerHTML.trim()),
                imgPath: theme.dataset.img || "",
                layoutStyles: theme.dataset.layoutStyles || "",
                name: theme.dataset.name,
                nowrap: hasDataOption(theme, "nowrap"),
                title: theme.getAttribute("title") || "",
                // TODO EGGMAIL: are there other themes without the builder?
                withBuilder: theme.dataset.name !== "basic",
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
            themeOptions.html = markup(
                renderToString("mass_mailing_egg.ThemeLayout", themeOptions)
            );
            this.loadedThemes.set(themeOptions.name, themeOptions);
        }
        this.loadedAssets.add(asset);
    }

    getThemeOptions(html) {
        if (!html) {
            return {};
        }
        const fragment = parseHTML(document, html);
        const layout = fragment.querySelector(".o_layout");
        if (!layout) {
            return {};
        }
        const themeClass = [...layout.classList].find(getNameFromClass);
        const themeName = getNameFromClass(themeClass);
        if (!themeName || !this.loadedThemes.has(themeName)) {
            return {};
        }
        return this.loadedThemes.get(themeName);
    }

    getThemes() {
        return this.loadedThemes.values();
    }

    isLoaded(asset = DEFAULT_ASSET) {
        return this.loadedAssets.has(asset);
    }

    async load(asset = DEFAULT_ASSET) {
        if (!this.isLoaded(asset)) {
            const themesHTML = await this.orm.silent.call(
                "ir.ui.view",
                "render_public_asset",
                [asset, {}],
                {}
            );
            const themesDocument = new DOMParser().parseFromString(themesHTML, "text/html").body;
            this.computeThemesTemplates(asset, themesDocument);
        }
    }
}

registry.category("services").add("mass_mailing_egg.themes", {
    dependencies: ["orm"],

    start(env, { orm }) {
        const services = { orm };
        return new ThemeModel(services);
    },
});
