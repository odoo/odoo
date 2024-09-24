import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { parseHTML } from "@html_editor/utils/html";
import { user } from "@web/core/user";
import { withSequence } from "@html_editor/utils/resource";

export class SignaturePlugin extends Plugin {
    static name = "signature";
    static dependencies = ["dom"];
    resources = {
        powerboxCategory: withSequence(100, { id: "basic_block", name: _t("Basic Bloc") }),
        powerboxItems: [
            {
                category: "basic_block",
                name: _t("Signature"),
                description: _t("Insert your signature"),
                fontawesome: "fa-pencil-square-o",
                action: () => {
                    return this.insertSignature();
                },
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
            this.shared.domInsert(parseHTML(this.document, currentUser.signature));
            this.dispatch("ADD_STEP");
        }
    }
}
