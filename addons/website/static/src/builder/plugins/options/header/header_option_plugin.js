import { Plugin } from "@html_editor/plugin";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { HeaderTemplateChoice, isHeaderBgBlurAvailable } from "./header_template_option";
import { HeaderTopOptions } from "./header_top_options";
import { CustomizeWebsiteColorAction, WebsiteConfigAction } from "../../customize_website_plugin";
import { isColorGradient } from "@web/core/utils/colors";

/** @typedef {import("@odoo/owl").Component} Component */

/**
 * @typedef { Object } HeaderOptionShared
 * @property { HeaderOptionPlugin['getHeaderTemplates'] } getHeaderTemplates
 */
/**
 * @typedef {(() => {
 *     key: string,
 *     Component: Component,
 *     props: any,
 * }[])[]} header_templates_providers
 */

export class HeaderOptionPlugin extends Plugin {
    static id = "headerOption";
    static dependencies = ["customizeWebsite", "menuDataPlugin"];
    static shared = ["getHeaderTemplates"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            HeaderTemplateConfigAction,
            CustomizeHeaderBackgroundAction,
            CustomizeHeaderBgBlurAction,
        },
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
        // we consider the container of Contact Us allows inline element at root
        // to avoid wrapping the button in a <p> or <div>, which would remove
        // this button if it's empty
        are_inlines_allowed_at_root_predicates: (node) =>
            node.matches(
                "#o_main_nav .oe_structure_solo .oe_unremovable [contenteditable='true']"
            ) || undefined,
        header_templates_providers: [
            () =>
                [
                    { name: "default", title: _t("Default") },
                    {
                        name: "hamburger",
                        title: _t("Hamburger Menu"),
                        extraViews: ["website.no_autohide_menu"],
                        defaultAlignment: {
                            mobile: "left",
                        },
                    },
                    { name: "boxed", title: _t("Rounded Box Menu") },
                    { name: "stretch", title: _t("Stretch Menu") },
                    {
                        name: "vertical",
                        title: _t("Vertical"),
                        defaultAlignment: {
                            desktop: "center",
                        },
                    },
                    { name: "search", title: _t("Menu with Search Bar") },
                    { name: "sales_one", title: _t("Menu - Sales 1") },
                    { name: "sales_two", title: _t("Menu - Sales 2") },
                    {
                        name: "sales_three",
                        title: _t("Menu - Sales 3"),
                        defaultAlignment: {
                            desktop: "right",
                        },
                    },
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
                            defaultAlignment: info.defaultAlignment,
                        },
                    };
                }),
        ],
    };

    setup() {
        this.headerTemplates = this.getResource("header_templates_providers").flatMap((provider) =>
            provider()
        );
    }

    getHeaderTemplates() {
        return this.headerTemplates;
    }
}

export class CustomizeHeaderBackgroundAction extends CustomizeWebsiteColorAction {
    static id = "customizeHeaderBackground";
    static dependencies = [...super.dependencies, "builderActions"];

    setup() {
        super.setup();
        this.websiteConfigAction = this.dependencies.builderActions.getAction("websiteConfig");
    }

    async apply(context) {
        const updatedColors = {};
        if (isColorGradient(context.value)) {
            updatedColors[context.params.gradientColor] = context.value;
            updatedColors[context.params.mainParam] = "";
        } else {
            updatedColors[context.params.mainParam] = context.value;
            updatedColors[context.params.gradientColor] = "";
        }
        const htmlStyle = getHtmlStyle(this.document);
        const headerBlurValue = parseFloat(getCSSVariableValue("header-bg-blur", htmlStyle));
        // Check that the blur classes are active on the header nav.
        const headerNavEl = this.document.querySelector("#wrapwrap header > nav");
        const hasBlurClasses =
            headerNavEl &&
            (headerNavEl.classList.contains("o_bg_blur_option") ||
                headerNavEl.classList.contains("o_bg_blur_no_enhance"));
        // If the background is no longer transparent, remove the blur.
        if (
            (headerBlurValue || hasBlurClasses) &&
            !isHeaderBgBlurAvailable(htmlStyle, updatedColors)
        ) {
            await this.websiteConfigAction.apply({
                params: {
                    views: ["!website.header_bg_blur", "!website.header_bg_blur_no_enhance"],
                    vars: { "header-bg-blur": 0 },
                },
            });
        }
        return super.apply(context);
    }
}

export class CustomizeHeaderBgBlurAction extends WebsiteConfigAction {
    static id = "customizeHeaderBgBlur";

    getValue() {
        return this.dependencies.customizeWebsite.getWebsiteVariableValue("header-bg-blur");
    }

    apply(context) {
        context.params = { ...context.params, vars: { "header-bg-blur": context.value } };
        return super.apply(context);
    }
}

export class HeaderTemplateConfigAction extends WebsiteConfigAction {
    static id = "headerTemplateConfig";

    async apply(applySpec) {
        const template = applySpec.params.views[0];
        const alignmentViews = getAlignmentViews(template, applySpec.params.defaultAlignment);
        applySpec.params.views.push(...alignmentViews);
        await super.apply(applySpec);
        return;
    }
}

/**
 * Returns the alignment view keys to enable/disable for the given header
 * template. "left" is the default so it has no dedicated view;
 * only "center" and "right" are toggled. "!" prefix means disable.
 *
 * @param {string} template - Fully-qualified header template view key
 * @param {object} [alignment]
 * @returns {string[]} View keys to activate or deactivate
 */
function getAlignmentViews(template, alignment) {
    const views = [];
    // If not alignment is set, then the default alignment is "desktop left"
    for (const direction of ["center", "right"]) {
        if (!alignment || "desktop" in alignment) {
            const view = template + `_align_${direction}`;
            views.push(alignment?.desktop === direction ? view : "!" + view);
        }
        if (alignment && "mobile" in alignment) {
            const view = template + `_mobile_align_${direction}`;
            views.push(alignment.mobile === direction ? view : "!" + view);
        }
    }
    return views;
}

registry.category("website-plugins").add(HeaderOptionPlugin.id, HeaderOptionPlugin);
