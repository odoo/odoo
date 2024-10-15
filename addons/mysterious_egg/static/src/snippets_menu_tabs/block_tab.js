import { Component, markup } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { RPCError } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";

function splitArrayBy3(arr) {
    const result = [];
    for (let i = 0; i < arr.length; i += 3) {
        result.push(arr.slice(i, i + 3));
    }
    return result;
}

export class BlockTab extends Component {
    static template = "mysterious_egg.BlockTab";

    setup() {
        this.dialog = useService("dialog");
        this.orm = useService("orm");
    }

    get snippetCategories() {
        return registry
            .category("website.snippets")
            .category("category")
            .getEntries()
            .filter(
                ([, category]) =>
                    category.isAvailable === undefined || category.isAvailable(this.env)
            );
    }

    get innerContentSnippets() {
        return registry
            .category("website.snippets")
            .category("inner_content")
            .getEntries()
            .filter(
                ([, category]) =>
                    category.isAvailable === undefined || category.isAvailable(this.env)
            );
    }

    get innerContentBy3() {
        const innertContents = registry
            .category("website.snippets")
            .category("inner_content")
            .getEntries()
            .filter(
                ([, category]) =>
                    category.isAvailable === undefined || category.isAvailable(this.env)
            );
        return splitArrayBy3(innertContents);
    }

    onClickInstall(snippet) {
        // TODO: Should be the app name, not the snippet name ... Maybe both ?
        const bodyText = _t("Do you want to install %s App?", snippet.title);
        const linkText = _t("More info about this app.");
        // TODO: extract moduleId;
        const linkUrl =
            "/odoo/action-base.open_module_tree/" + encodeURIComponent(snippet.moduleId);

        this.dialog.add(ConfirmationDialog, {
            title: _t("Install %s", snippet.title),
            body: markup(
                `${escape(bodyText)}\n<a href="${linkUrl}" target="_blank">${escape(linkText)}</a>`
            ),
            confirm: async () => {
                try {
                    await this.orm.call("ir.module.module", "button_immediate_install", [
                        [snippet.install],
                    ]);
                    this.invalidateSnippetCache = true;

                    // TODO Need to Reload webclient
                    // this._onSaveRequest({
                    //     data: {
                    //         reloadWebClient: true,
                    //     },
                    // });
                } catch (e) {
                    if (e instanceof RPCError) {
                        const message = escape(_t("Could not install module %s", snippet.title));
                        this.notification.add(message, {
                            type: "danger",
                            sticky: true,
                        });
                        return;
                    }
                    throw e;
                }
            },
            confirmLabel: _t("Save and Install"),
            cancel: () => {},
        });
    }
}
