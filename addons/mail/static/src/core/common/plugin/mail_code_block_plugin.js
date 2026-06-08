import { CodeBlockPlugin } from "@html_editor/main/code_block_plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";

export class MailCodeBlockPlugin extends CodeBlockPlugin {
    static id = "mailCodeBlock";

    resources = Object.assign(this.resources, {
        toolbar_items: [
            withSequence(25, {
                id: "code_block",
                groupId: "layout",
                namespaces: ["compact", "expanded"],
                commandId: "setTagPre",
                description: _t("Insert code block"),
            }),
        ],
    });
}
