import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { rpc } from "@web/core/network/rpc";

class FooterOptionPlugin extends Plugin {
    static id = "footerOption";
    static dependencies = ["customizeWebsite", "builderActions"];

    resources = {
        builder_options: [
            withSequence(1, {
                template: "html_builder.FooterTemplateOption",
                selector: "#wrapwrap > footer",
                editableOnly: false,
                groups: ["website.group_website_designer"],
            }),
            withSequence(10, {
                template: "html_builder.FooterWidthOption",
                selector: "#wrapwrap > footer",
                applyTo:
                    ":is(:scope > #footer > section, .o_footer_copyright) > :is(.container, .container-fluid, .o_container_small)",
                editableOnly: false,
                groups: ["website.group_website_designer"],
            }),
            {
                template: "html_builder.FooterScrollToTopOption",
                selector: "#wrapwrap > footer",
                editableOnly: false,
                groups: ["website.group_website_designer"],
            },
        ],
        builder_actions: {
            websiteConfigFooter: {
                reload: {},
                isApplied: ({ param: { vars } }) => {
                    for (const [name, value] of Object.entries(vars)) {
                        if (
                            !this.dependencies.builderActions
                                .getAction("customizeWebsiteVariable")
                                .isApplied({ param: { mainParam: name }, value })
                        ) {
                            return false;
                        }
                    }
                    return true;
                },
                apply: async ({ param: { vars, view }, selectableContext }) => {
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
                },
            },
        },
    };
}

registry.category("website-plugins").add(FooterOptionPlugin.id, FooterOptionPlugin);
