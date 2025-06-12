import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { rpc } from "@web/core/network/rpc";
import { after, SNIPPET_SPECIFIC_NEXT } from "@html_builder/utils/option_sequence";
import { BuilderAction } from "@html_builder/core/builder_action";

export const FOOTER_TEMPLATE = SNIPPET_SPECIFIC_NEXT;
export const FOOTER_WIDTH = after(FOOTER_TEMPLATE);
export const FOOTER_SLIDEOUT = after(FOOTER_WIDTH);
export const FOOTER_BORDER = after(FOOTER_SLIDEOUT);
export const FOOTER_COLORS = after(FOOTER_BORDER);
export const FOOTER_SCROLL_TO = after(FOOTER_COLORS);
export const FOOTER_COPYRIGHT = after(FOOTER_SCROLL_TO);

class FooterOptionPlugin extends Plugin {
    static id = "footerOption";
    static dependencies = ["customizeWebsite", "builderActions"];

    resources = {
        builder_options: [
            withSequence(FOOTER_TEMPLATE, {
                template: "website.FooterTemplateOption",
                selector: "#wrapwrap > footer",
                editableOnly: false,
                groups: ["website.group_website_designer"],
            }),
            withSequence(FOOTER_WIDTH, {
                template: "website.FooterWidthOption",
                selector: "#wrapwrap > footer",
                applyTo:
                    ":is(:scope > #footer > section, .o_footer_copyright) > :is(.container, .container-fluid, .o_container_small)",
                editableOnly: false,
                groups: ["website.group_website_designer"],
            }),
            withSequence(FOOTER_COLORS, {
                template: "website.FooterColorsOption",
                selector: "#wrapwrap > footer",
                editableOnly: false,
                groups: ["website.group_website_designer"],
            }),
            withSequence(FOOTER_SLIDEOUT, {
                template: "website.FooterSlideoutOption",
                selector: "#wrapwrap > footer",
                editableOnly: false,
                groups: ["website.group_website_designer"],
            }),
            withSequence(FOOTER_COPYRIGHT, {
                template: "website.ToggleFooterCopyrightOption",
                selector: "#wrapwrap > footer",
                editableOnly: false,
                groups: ["website.group_website_designer"],
            }),
            withSequence(FOOTER_BORDER, {
                template: "website.FooterBorder",
                selector: "#wrapwrap > footer",
                applyTo: "#footer",
                editableOnly: false,
                groups: ["website.group_website_designer"],
            }),
            withSequence(FOOTER_SCROLL_TO, {
                template: "website.FooterScrollToTopOption",
                selector: "#wrapwrap > footer",
                editableOnly: false,
                groups: ["website.group_website_designer"],
            }),
        ],
        builder_actions: {
            WebsiteConfigFooterAction,
        },
        on_prepare_drag_handlers: this.prepareDrag.bind(this),
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
