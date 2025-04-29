import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

const mainObjectRe = /website\.controller\.page\(((\d+,?)*)\)/;

class ControllerPageListingLayoutOptionPlugin extends Plugin {
    static id = "controllerPageListingLayoutOption";
    static dependencies = ["builderActions"];
    resources = {
        builder_options: [
            {
                template: "html_builder.website.ControllerPageListingLayoutOption",
                selector: ".listing_layout_switcher",
                editableOnly: false,
                title: _t("Layout"),
                groups: ["website.group_website_designer"],
            },
        ],
        builder_actions: this.getActions(),
    };
    setup() {
        this.layout = undefined;
        this.resIds = undefined;
    }
    getActions() {
        return [
            {
                listingLayout: {
                    reload: {},
                    prepare: async () => {
                        const mainObjectRepr =
                            this.document.documentElement.getAttribute("data-main-object");
                        const match = mainObjectRe.exec(mainObjectRepr);
                        if (match && match[1]) {
                            this.resIds = match[1].split(",").flatMap((e) => {
                                if (!e) {
                                    return [];
                                }
                                const id = parseInt(e);
                                return id ? [id] : [];
                            });
                        }
                        const results = await this.services.orm.read(
                            "website.controller.page",
                            this.resIds,
                            ["default_layout"]
                        );
                        this.layout = results[0]["default_layout"];
                    },
                    getValue: () => this.layout,
                    isApplied: ({ value }) => this.layout === value,
                    apply: async ({ editingElement: el, value }) => {
                        const params = {
                            layout_mode: value,
                            view_id: el.dataset.viewId,
                        };
                        // Save the default layout display, and set the layout for the current user
                        await Promise.all([
                            this.services.orm.write("website.controller.page", this.resIds, {
                                default_layout: value,
                            }),
                            rpc("/website/save_session_layout_mode", params),
                        ]);
                    },
                },
            },
        ];
    }
}
registry
    .category("website-plugins")
    .add(ControllerPageListingLayoutOptionPlugin.id, ControllerPageListingLayoutOptionPlugin);
