import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { setDatasetIfUndefined } from "./dynamic_snippet_option_plugin";
import { InstagramAccountDialog } from "./instagram_account_dialog";

export class InstagramCarouselOptionPlugin extends Plugin {
    static id = "instagramCarouselOption";
    static shared = ["connectAccount"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            InstagramAccountAction,
            ConnectInstagramAccountAction,
        },
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        // Clicking on a post or on the title selects an inner section, which
        // has no option: show the options of the snippet instead.
        auto_unfold_container_providers: {
            selector: ".s_dynamic_snippet_instagram section",
            target: ".s_dynamic_snippet_instagram",
        },
    };

    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(".s_dynamic_snippet_instagram")) {
            if (!snippetEl.dataset.numberOfRecords) {
                snippetEl.dataset.numberOfRecords = "8";
            }
            setDatasetIfUndefined(snippetEl, "numberOfElements", "4");
            setDatasetIfUndefined(snippetEl, "carouselInterval", "5000");
            const [account] = await this.services.orm.call(
                "website.instagram.account",
                "name_search",
                [""],
                { limit: 1 }
            );
            const accountId =
                account?.[0] ||
                ((await user.hasGroup("website.group_website_designer")) &&
                    (await this.connectAccount()));
            if (accountId) {
                snippetEl.dataset.instagramAccountId = accountId;
            }
        }
    }

    /**
     * Open the dialog to connect an Instagram account.
     *
     * @returns {Promise<number|undefined>} the id of the connected account, if
     * any.
     */
    connectAccount() {
        return new Promise((resolve) => {
            let accountId;
            this.services.dialog.add(
                InstagramAccountDialog,
                {
                    onConnect: (connectedAccountId) => {
                        accountId = connectedAccountId;
                    },
                },
                { onClose: () => resolve(accountId) }
            );
        });
    }
}

/**
 * Select the account of the snippet, as a `BuilderMany2One` value.
 */
export class InstagramAccountAction extends BuilderAction {
    static id = "instagramAccount";
    apply({ editingElement, value }) {
        editingElement.dataset.instagramAccountId = JSON.parse(value).id;
    }
    clean({ editingElement }) {
        delete editingElement.dataset.instagramAccountId;
    }
    getValue({ editingElement }) {
        const accountId = editingElement.dataset.instagramAccountId;
        return accountId && JSON.stringify({ id: parseInt(accountId) });
    }
}

export class ConnectInstagramAccountAction extends BuilderAction {
    static id = "connectInstagramAccount";
    static dependencies = ["instagramCarouselOption"];
    load() {
        return this.dependencies.instagramCarouselOption.connectAccount();
    }
    apply({ editingElement, loadResult: accountId }) {
        if (accountId) {
            editingElement.dataset.instagramAccountId = accountId;
        }
    }
}

registry
    .category("website-plugins")
    .add(InstagramCarouselOptionPlugin.id, InstagramCarouselOptionPlugin);
