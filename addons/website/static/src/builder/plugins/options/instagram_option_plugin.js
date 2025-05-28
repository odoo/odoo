import { SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { getCommonAncestor, selectElements } from "@html_editor/utils/dom_traversal";
import { withSequence } from "@html_editor/utils/resource";

class InstagramOptionPlugin extends Plugin {
    static id = "instagramOption";
    static dependencies = ["history"];

    resources = {
        builder_options: [
            withSequence(SNIPPET_SPECIFIC_END, {
                template: "website.InstagramOption",
                selector: ".s_instagram_page",
            }),
        ],
        builder_actions: {
            instagramPageAction: {
                getValue: ({ editingElement }) => editingElement.dataset["instagramPage"],
                apply: ({ editingElement, value }) => {
                    delete editingElement.dataset.instagramPageIsDefault;
                    if (value.includes(this.instagramUrlStr)) {
                        value = this.instagramPageNameFromUrl(value) || "";
                    }
                    editingElement.dataset["instagramPage"] = value;
                    if (value === "") {
                        this.services.notification.add(_t("The Instagram page name is not valid"), {
                            type: "warning",
                        });
                    }
                },
            },
        },
        normalize_handlers: this.normalize.bind(this),
    };

    setup() {
        this.instagramUrlStr = "instagram.com/";
    }

    normalize(root) {
        const nodes = [
            ...selectElements(root, ".s_instagram_page[data-instagram-page-is-default]"),
        ];
        if (nodes.length) {
            this.loadAndSetPage(nodes);
        }
    }

    async loadAndSetPage(nodes) {
        // TODO: look in shared cache with social info: was SocialMediaOption.getDbSocialValuesCache()
        if (this.instagramUrl) {
            this.setPage(nodes);
            return;
        }
        // Fetches the default url for instagram page from website config
        const res = await this.services.orm.read(
            "website",
            [this.services.website.currentWebsite.id],
            ["social_instagram"]
        );
        if (res && res[0].social_instagram) {
            this.instagramUrl = this.instagramPageNameFromUrl(res[0].social_instagram);

            // WARNING: the call to ignoreDOMMutations is very dangerous,
            // and should be avoided in most cases (if you think you need those, ask html_editor team)
            const hasChanged = this.dependencies.history.ignoreDOMMutations(() =>
                this.setPage(nodes)
            );

            if (hasChanged) {
                const commonAncestor = getCommonAncestor(nodes, this.editable);
                this.dispatchTo("content_manually_updated_handlers", commonAncestor);
                this.config.onChange({ isPreviewing: false });
            }
        }
    }

    setPage(nodes) {
        let hasChanged = false;
        for (const element of nodes) {
            if (element.dataset.instagramPageIsDefault) {
                delete element.dataset.instagramPageIsDefault;
                if (this.instagramUrl) {
                    element.dataset.instagramPage = this.instagramUrl;
                }
                hasChanged = true;
            }
        }
        return hasChanged;
    }

    /**
     * Returns the instagram page name from the given url.
     *
     * @private
     * @param {string} url
     * @returns {string|undefined}
     */
    instagramPageNameFromUrl(url) {
        const pageName = url.split(this.instagramUrlStr)[1];
        if (
            !pageName ||
            pageName.includes("?") ||
            pageName.includes("#") ||
            (pageName.includes("/") && pageName.split("/")[1].length > 0)
        ) {
            return;
        }
        return pageName.split("/")[0];
    }
}

registry.category("website-plugins").add(InstagramOptionPlugin.id, InstagramOptionPlugin);
