import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { rpc } from "@web/core/network/rpc";
import { after, SNIPPET_SPECIFIC_NEXT } from "@html_builder/utils/option_sequence";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { ShadowOption } from "@html_builder/plugins/shadow_option";

export const FOOTER_TEMPLATE = SNIPPET_SPECIFIC_NEXT;
export const FOOTER_WIDTH = after(FOOTER_TEMPLATE);
export const FOOTER_SLIDEOUT = after(FOOTER_WIDTH);
export const FOOTER_BORDER = after(FOOTER_SLIDEOUT);
export const FOOTER_COLORS = after(FOOTER_BORDER);
export const FOOTER_SCROLL_TO = after(FOOTER_COLORS);
export const FOOTER_COPYRIGHT = after(FOOTER_SCROLL_TO);

export class FooterTemplateOption extends BaseOptionComponent {
    static template = "website.FooterTemplateOption";
    static selector = "#wrapwrap > footer";
    static editableOnly = false;
    static groups = ["website.group_website_designer"];
}

export class FooterWidthOption extends BaseOptionComponent {
    static template = "website.FooterWidthOption";
    static selector = "#wrapwrap > footer";
    static applyTo =
        ":is(:scope > #footer > section, .o_footer_copyright) > :is(.container, .container-fluid, .o_container_small)";
    static editableOnly = false;
    static groups = ["website.group_website_designer"];
}

export class FooterColorsOption extends BaseOptionComponent {
    static template = "website.FooterColorsOption";
    static selector = "#wrapwrap > footer";
    static editableOnly = false;
    static groups = ["website.group_website_designer"];
}

export class FooterSlideoutOption extends BaseOptionComponent {
    static template = "website.FooterSlideoutOption";
    static selector = "#wrapwrap > footer";
    static editableOnly = false;
    static groups = ["website.group_website_designer"];
}

export class ToggleFooterCopyrightOption extends BaseOptionComponent {
    static template = "website.ToggleFooterCopyrightOption";
    static selector = "#wrapwrap > footer";
    static editableOnly = false;
    static groups = ["website.group_website_designer"];
}

export class FooterBorder extends BaseOptionComponent {
    static template = "website.FooterBorder";
    static selector = "#wrapwrap > footer";
    static applyTo = "#footer";
    static editableOnly = false;
    static groups = ["website.group_website_designer"];
    static components = { BorderConfigurator, ShadowOption };
}

export class FooterScrollToTopOption extends BaseOptionComponent {
    static template = "website.FooterScrollToTopOption";
    static selector = "#wrapwrap > footer";
    static editableOnly = false;
    static groups = ["website.group_website_designer"];
}

class FooterOptionPlugin extends Plugin {
    static id = "footerOption";
    static dependencies = ["customizeWebsite", "builderActions"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [
            withSequence(FOOTER_TEMPLATE, FooterTemplateOption),
            withSequence(FOOTER_WIDTH, FooterWidthOption),
            withSequence(FOOTER_COLORS, FooterColorsOption),
            withSequence(FOOTER_SLIDEOUT, FooterSlideoutOption),
            withSequence(FOOTER_COPYRIGHT, ToggleFooterCopyrightOption),
            withSequence(FOOTER_BORDER, FooterBorder),
            withSequence(FOOTER_SCROLL_TO, FooterScrollToTopOption),
        ],
        builder_actions: {
            WebsiteConfigFooterAction,
        },
        on_prepare_drag_handlers: this.prepareDrag.bind(this),
        unremovable_node_predicates: (node) => node.id === "o_footer_scrolltop",
    };

    prepareDrag() {
        // Remove the footer scroll effect if it has one (because the footer
        // dropzone flickers otherwise when it is in grid mode).
        let restore = () => {};
        const wrapwrapEl = this.editable;
        const hasFooterScrollEffect = wrapwrapEl.classList.contains("o_footer_effect_enable");
        if (hasFooterScrollEffect) {
            wrapwrapEl.classList.remove("o_footer_effect_enable");
            restore = () => {
                wrapwrapEl.classList.add("o_footer_effect_enable");
            };
        }
        return restore;
    }
}

export class WebsiteConfigFooterAction extends BuilderAction {
    static id = "websiteConfigFooter";
    static dependencies = ["builderActions", "customizeWebsite"];
    setup() {
        this.reload = {};
    }
    isApplied({ params: { vars } }) {
        for (const [name, value] of Object.entries(vars)) {
            if (
                !this.dependencies.builderActions
                    .getAction("customizeWebsiteVariable")
                    .isApplied({ params: { mainParam: name }, value })
            ) {
                return false;
            }
        }
        return true;
    }
    async apply({ params: { vars, view }, selectableContext }) {
        const possibleValues = new Set();
        for (const item of selectableContext.items) {
            for (const a of item.getActions()) {
                if (a.actionId === "websiteConfigFooter") {
                    possibleValues.add(a.actionParam.view);
                }
            }
        }
        await Promise.all([
            this.dependencies.customizeWebsite.makeSCSSCusto(
                "/website/static/src/scss/options/user_values.scss",
                vars
            ),
            rpc("/website/update_footer_template", {
                template_key: view,
                possible_values: [...possibleValues],
            }),
        ]);
    }
}

registry.category("website-plugins").add(FooterOptionPlugin.id, FooterOptionPlugin);
