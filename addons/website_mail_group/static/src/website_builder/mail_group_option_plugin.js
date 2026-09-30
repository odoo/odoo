import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { InputConfirmationDialog } from "@html_builder/snippets/input_confirmation_dialog";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class MailGroupOption extends BaseOptionComponent {
    static template = "website_mail_group.MailGroupOption";
    static selector = ".s_group";
}

class MailGroupOptionPlugin extends Plugin {
    static id = "mailGroupOption";
    static dependencies = ["builderActions"];
    static shared = ["createGroup"];
    resources = {
        builder_options: [MailGroupOption],
        dropzone_selector: {
            selector: ".s_group",
            dropNear: "p, h1, h2, h3, blockquote, .card",
            dropIn: ".row.o_grid_mode",
        },
        builder_actions: {
            MailGroupAction,
            CreateMailGroupAction,
        },
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.dataset.snippet !== "s_group") {
            return;
        }
        const group = await this.services.orm.call("mail.group", "name_search", [""], { limit: 1 });
        if (this.isDestroyed) {
            return;
        }
        const id = group[0]?.[0] || (await this.createGroup());
        if (!id) {
            return true; // cancel snippet
        }
        snippetEl.dataset.id = id;
    }

    async createGroup(value) {
        let name;
        await new Promise((resolve) => {
            this.services.dialog.add(
                InputConfirmationDialog,
                {
                    title: _t("New Mail Group"),
                    inputLabel: _t("Name"),
                    defaultValue: value,
                    confirm: (confirmedValue) => {
                        name = confirmedValue;
                    },
                },
                { onClose: resolve }
            );
        });
        if (name) {
            return await this.services.orm.create("mail.group", [{ name }]);
        }
    }
}

export class MailGroupAction extends BuilderAction {
    static id = "mailGroupAction"
    static dependencies = ["builderActions"];
    apply({ editingElement, value }) {
        const { id } = JSON.parse(value);

        this.dependencies.builderActions
            .getAction("dataAttributeAction")
            .apply({ editingElement, params: { mainParam: "id" }, value: id });
    }
    clean({ editingElement }) {
        this.dependencies.builderActions
            .getAction("dataAttributeAction")
            .clean({ editingElement, params: { mainParam: "id" } });
    }
    getValue({ editingElement }) {
        const value = {};
        const id = this.dependencies.builderActions
            .getAction("dataAttributeAction")
            .getValue({ editingElement, params: { mainParam: "id" } });
        if (!id) {
            return;
        }
        value.id = parseInt(id);
        return JSON.stringify(value);
    }
}
export class CreateMailGroupAction extends BuilderAction {
    static id = "createMailGroup";
    static dependencies = ["builderActions", "mailGroupOption"];
    load({ value }) {
        return this.dependencies.mailGroupOption.createGroup(value);
    }
    apply({ editingElement, loadResult: id }) {
        if (id) {
            this.dependencies.builderActions
                .getAction("mailGroupAction")
                .apply({ editingElement, value: JSON.stringify({ id }) });
        }
    }
}

registry.category("website-plugins").add(MailGroupOptionPlugin.id, MailGroupOptionPlugin);
