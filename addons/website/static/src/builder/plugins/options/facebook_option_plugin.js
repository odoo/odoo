import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { getCommonAncestor, selectElements } from "@html_editor/utils/dom_traversal";
import { BuilderAction } from "@html_builder/core/builder_action";
import { getFacebookPageId } from "@website/js/utils";

export class FacebookOptionPlugin extends Plugin {
    static id = "facebookOption";
    static dependencies = ["domObserver"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        so_content_addition_selectors: [".o_facebook_page"],
        builder_actions: {
            DataAttributeListAction,
            CheckFacebookLinkAction,
        },
        normalize_processors: this.normalize.bind(this),
        content_not_editable_selectors: ".o_facebook_page",
    };

    normalize(root) {
        for (const element of selectElements(root, ".o_facebook_page")) {
            let desiredHeight;
            if (element.dataset.tabs) {
                desiredHeight = element.dataset.tabs === "events" ? 300 : 500;
            } else if (element.dataset.small_header) {
                desiredHeight = 70;
            } else {
                desiredHeight = 150;
            }
            if (desiredHeight !== element.dataset.height) {
                element.dataset.height = desiredHeight;
            }
        }

        const nodes = selectElements(root, ".o_facebook_page:not([data-href])");
        if (nodes.length) {
            this.loadAndSetEmptyLink(nodes);
        }
        return root;
    }

    async loadAndSetEmptyLink(nodes) {
        // TODO: look in shared cache with social info: was SocialMediaOption.getDbSocialValuesCache()
        if (this.facebookUrl) {
            this.setEmptyLink(nodes);
            return;
        }
        // Fetches the default url for facebook page from company config
        const res = await this.services.orm.read(
            "res.company",
            [this.services.website.currentWebsite.company_id],
            ["social_facebook"]
        );
        if (res) {
            this.facebookUrl = res[0].social_facebook || "https://www.facebook.com/Odoo";

            // WARNING: the call to ignore is very dangerous,
            // and should be avoided in most cases (if you think you need those, ask html_editor team)
            const hasChanged = this.dependencies.domObserver.ignore(() => this.setEmptyLink(nodes));

            if (hasChanged) {
                const commonAncestor = getCommonAncestor(nodes, this.editable);
                this.trigger("on_content_manually_updated_handlers", commonAncestor);
                this.config.onChange({ isPreviewing: false });
            }
        }
    }

    setEmptyLink(nodes) {
        let hasChanged = false;
        for (const element of nodes) {
            if (!element.dataset.href) {
                element.dataset.href = this.facebookUrl;
                hasChanged = true;
            }
        }
        return hasChanged;
    }
}

export class DataAttributeListAction extends BuilderAction {
    static id = "dataAttributeList";
    isApplied({ editingElement, params: { mainParam } = {}, value }) {
        return (editingElement.dataset[mainParam]?.split(",") || []).includes(value);
    }
    apply({ editingElement, params: { mainParam } = {}, value }) {
        editingElement.dataset[mainParam] = [
            ...(editingElement.dataset[mainParam]?.split(",") || []),
            value,
        ].join(",");
    }
    clean({ editingElement, params: { mainParam } = {}, value }) {
        editingElement.dataset[mainParam] = (editingElement.dataset[mainParam]?.split(",") || [])
            .filter((e) => e !== value)
            .join(",");
    }
}
export class CheckFacebookLinkAction extends BuilderAction {
    static id = "checkFacebookLink";
    setup() {
        this.closeNotif = () => {};
    }
    apply({ editingElement, value }) {
        editingElement.dataset.id = "";
        const id = getFacebookPageId(value);
        if (id) {
            editingElement.dataset.id = id;
            this.checkFacebookId(id).then((ok) => {
                this.closeNotif();
                if (ok) {
                    this.closeNotif = () => {};
                } else {
                    this.closeNotif = this.services.notification.add(
                        _t("We couldn't find the Facebook page"),
                        { type: "warning" }
                    );
                }
            });
        } else {
            this.closeNotif();
            this.closeNotif = this.services.notification.add(
                _t("You didn't provide a valid Facebook link"),
                { type: "warning" }
            );
        }
    }
    async checkFacebookId(id) {
        const res = await fetch(`https://graph.facebook.com/${id}/picture`);
        return res.ok;
    }
}

registry.category("website-plugins").add(FacebookOptionPlugin.id, FacebookOptionPlugin);
