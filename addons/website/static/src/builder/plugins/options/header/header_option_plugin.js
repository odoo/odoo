import {
    SNIPPET_SPECIFIC_END,
    SNIPPET_SPECIFIC_NEXT,
    splitBetween,
} from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { reactive } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { HeaderElementsOption } from "./header_elements_option";
import { HeaderFontOption } from "./header_font_option";
import { HeaderTemplateChoice, HeaderTemplateOption } from "./header_template_option";
import { HeaderIconBackgroundOption } from "./header_icon_background_option";
import { HeaderTopOptions } from "./header_top_options";

/** @typedef {import("@odoo/owl").Component} Component */

/**
 * @typedef { Object } HeaderOptionShared
 * @property { HeaderOptionPlugin['getHeaderTemplates'] } getHeaderTemplates
 */
/**
 * @typedef {(() => Promise<{
 *     key: string,
 *     Component: Component,
 *     props: any,
 * }[]>)[]} header_templates_providers
 */

const [
    HEADER_TEMPLATE,
    HEADER_FONT,
    HEADER_BOX,
    HEADER_NAVIGATION,
    HEADER_ELEMENTS,
    HEADER_ICON_BACKGROUND,
    HEADER_END,
    ...__ERROR_CHECK__
] = splitBetween(SNIPPET_SPECIFIC_NEXT, SNIPPET_SPECIFIC_END, 7);
if (__ERROR_CHECK__.length > 0) {
    console.error("Wrong count in header option split");
}

export {
    HEADER_TEMPLATE,
    HEADER_FONT,
    HEADER_BOX,
    HEADER_NAVIGATION,
    HEADER_ELEMENTS,
    HEADER_ICON_BACKGROUND,
    HEADER_END,
};

class HeaderOptionPlugin extends Plugin {
    static id = "headerOption";
    static dependencies = ["customizeWebsite", "menuDataPlugin"];
    static shared = ["getHeaderTemplates"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_header_middle_buttons: [
            {
                Component: HeaderTopOptions,
                editableOnly: false,
                selector: "#wrapwrap > header",
                props: {
                    openEditMenu: () => this.dependencies.menuDataPlugin.openEditMenu(),
                },
            },
        ],
        builder_options: [
            withSequence(HEADER_TEMPLATE, HeaderTemplateOption),
            withSequence(HEADER_FONT, HeaderFontOption),
            withSequence(HEADER_ELEMENTS, HeaderElementsOption),
            withSequence(HEADER_ICON_BACKGROUND, HeaderIconBackgroundOption),
        ],
        header_templates_providers: [
            () =>
                [
                    { name: "default", title: _t("Default") },
                    {
                        name: "hamburger",
                        title: _t("Hamburger Menu"),
                        extraViews: ["website.no_autohide_menu"],
                    },
                    { name: "boxed", title: _t("Rounded Box Menu") },
                    { name: "stretch", title: _t("Stretch Menu") },
                    { name: "vertical", title: _t("Vertical") },
                    { name: "search", title: _t("Menu with Search Bar") },
                    { name: "sales_one", title: _t("Menu - Sales 1") },
                    { name: "sales_two", title: _t("Menu - Sales 2") },
                    { name: "sales_three", title: _t("Menu - Sales 3") },
                    { name: "sales_four", title: _t("Menu - Sales 4") },
                    {
                        name: "sidebar",
                        title: _t("Sidebar"),
                        extraViews: ["website.no_autohide_menu"],
                        menuShadowClass: "shadow-lg",
                    },
                ].map((info) => {
                    const view = info.view ?? `website.template_header_${info.name}`;
                    return {
                        key: info.name,
                        Component: HeaderTemplateChoice,
                        props: {
                            id: `header_${info.name}_opt`,
                            imgSrc: `/website/static/src/img/snippets_options/header_template_${info.name}.svg`,
                            menuShadowClass: info.menuShadowClass ?? "shadow-sm",
                            title: info.title,
                            varName: info.name,
                            views: [view, ...(info.extraViews || [])],
                        },
                    };
                }),
        ],
    };

    getHeaderTemplates() {
        const templates = reactive([]);

        // we don't wait for all promises to resolve and show the ones available
        // as soon as they are (and keep them in the order of the providers)
        const templatesByProvider = this.getResource("header_templates_providers").map((p) => {
            const provided = [];
            Promise.resolve(p()).then((t) => {
                provided.push(...t);
                templates.splice(0, Infinity, ...templatesByProvider.flat());
            });
            return provided;
        });

        return templates;
    }
}

registry.category("website-plugins").add(HeaderOptionPlugin.id, HeaderOptionPlugin);
