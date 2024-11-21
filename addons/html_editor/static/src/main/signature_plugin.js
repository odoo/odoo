import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { parseHTML } from "@html_editor/utils/html";
import { user } from "@web/core/user";
import { withSequence } from "@html_editor/utils/resource";

export class SignaturePlugin extends Plugin {
    static id = "signature";
    static dependencies = ["dom", "history"];
    resources = {
        user_commands: [
            {
                id: "insertSignature",
                title: _t("Signature"),
                description: _t("Insert your signature"),
                icon: "fa-pencil-square-o",
                run: this.insertSignature.bind(this),
            },
        ],
        powerbox_categories: withSequence(100, { id: "basic_block", name: _t("Basic Bloc") }),
        powerbox_items: [
            {
                categoryId: "basic_block",
                commandId: "insertSignature",
            },
        ],
    };

    async insertSignature() {
        const [currentUser] = await this.services.orm.read(
            "res.users",
            [user.userId],
            ["signature"]
        );
        if (currentUser && currentUser.signature) {
            this.dependencies.dom.insert(parseHTML(this.document, currentUser.signature));
            this.dependencies.history.addStep();
        }
    }
}
