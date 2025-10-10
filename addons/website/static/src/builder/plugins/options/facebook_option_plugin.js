import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { getCommonAncestor, selectElements } from "@html_editor/utils/dom_traversal";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class FacebookOption extends BaseOptionComponent {
    static template = "website.FacebookOption";
    static selector = ".o_facebook_page";
}

class FacebookOptionPlugin extends Plugin {
    static id = "facebookOption";
    static dependencies = ["history"];
    resources = {
        builder_options: [FacebookOption],
        so_content_addition_selector: [".o_facebook_page"],
        builder_actions: {
            DataAttributeListAction,
            CheckFacebookLinkAction,
        },
        normalize_handlers: this.normalize.bind(this),
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

        const nodes = [...selectElements(root, ".o_facebook_page:not([data-href])")];
        if (nodes.length) {
            this.loadAndSetEmptyLink(nodes);
        }
    }

    async loadAndSetEmptyLink(nodes) {
        // TODO: look in shared cache with social info: was SocialMediaOption.getDbSocialValuesCache()
        if (this.facebookUrl) {
            this.setEmptyLink(nodes);
            return;
        }
        // Fetches the default url for facebook page from website config
        const res = await this.services.orm.read(
            "website",
            [this.services.website.currentWebsite.id],
            ["social_facebook"]
        );
        if (res) {
            this.facebookUrl = res[0].social_facebook || "https://www.facebook.com/Odoo";

            // WARNING: the call to ignoreDOMMutations is very dangerous,
            // and should be avoided in most cases (if you think you need those, ask html_editor team)
            const hasChanged = this.dependencies.history.ignoreDOMMutations(() =>
                this.setEmptyLink(nodes)
            );

            if (hasChanged) {
                const commonAncestor = getCommonAncestor(nodes, this.editable);
                this.dispatchTo("content_manually_updated_handlers", commonAncestor);
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
        const id = this.idFromFacebookLink(value);
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
    idFromFacebookLink(url) {
        // Patterns matched by the regex (all relate to existing pages,
        // in spite of the URLs containing "profile.php" or "people"):
        // - https://www.facebook.com/<pagewithaname>
        // - http://www.facebook.com/<page.with.a.name>
        // - www.facebook.com/<fbid>
        // - facebook.com/profile.php?id=<fbid>
        // - www.facebook.com/<name>-<fbid>  - NB: the name doesn't matter
        // - www.fb.com/people/<name>/<fbid>  - same
        // - m.facebook.com/p/<name>-<fbid>  - same
        // The regex is kept as a huge one-liner for performance as it is
        // compiled once on script load. The only way to split it on several
        // lines is with the RegExp constructor, which is compiled on runtime.
        const match = url
            .trim()
            .match(
                /^(https?:\/\/)?((www\.)?(fb|facebook)|(m\.)?facebook)\.com\/(((profile\.php\?id=|people\/([^/?#]+\/)?|(p\/)?[^/?#]+-)(?<id>[0-9]{12,16}))|(?<nameid>[\w.]+))($|[/?# ])/
            );

        return match?.groups.nameid || match?.groups.id;
    }

    async checkFacebookId(id) {
        const res = await fetch(`https://graph.facebook.com/${id}/picture`);
        return res.ok;
    }
}

registry.category("website-plugins").add(FacebookOptionPlugin.id, FacebookOptionPlugin);
