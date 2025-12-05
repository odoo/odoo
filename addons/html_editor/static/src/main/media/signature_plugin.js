import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { SignatureDialog } from "@web/core/signature/signature_dialog";
import { user } from "@web/core/user";

export class SignaturePlugin extends Plugin {
    static id = "signature";
    static dependencies = ["dom", "history", "media"];
    resources = {
        user_commands: [
            {
                id: "insertSignature",
                title: _t("Signature"),
                description: _t("Insert your signature"),
                icon: "fa-pencil-square-o",
                run: this.insertSignature.bind(this),
                isAvailable: (selection) =>
                    this.config.allowImage && isHtmlContentSupported(selection),
            },
        ],
        powerbox_items: [
            {
                categoryId: "media",
                commandId: "insertSignature",
            },
        ],
    };

    insertSignature() {
        this.services.dialog.add(SignatureDialog, {
            defaultName: user.name,
            nameAndSignatureProps: {
                displaySignatureRatio: 3,
            },
            uploadSignature: (signature) => {
                const img = document.createElement("img");
                img.classList.add("img", "img-fluid", "o_we_custom_image");
                img.style = "width: 50%";
                img.src = signature.signatureImage;
                this.dependencies.dom.insert(img);
                this.dependencies.history.addStep();
                close();
            },
        });
    }
}
