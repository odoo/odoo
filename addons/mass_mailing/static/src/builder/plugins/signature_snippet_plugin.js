import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { Plugin } from "@html_editor/plugin";
import { SignatureDialog } from "@web/core/signature/signature_dialog";

export class MassMailingSignatureSnippetPlugin extends Plugin {
    static id = "mass_mailing.signatureSnippet";
    resources = {
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    async onSnippetDropped({ snippetEl }) {
        const images = snippetEl.querySelectorAll(".o_mail_signature_image");
        if (!images.length) {
            return;
        }
        this.services.dialog.add(
            SignatureDialog,
            {
                defaultName: user.name,
                nameAndSignatureProps: {
                    displaySignatureRatio: 3,
                },
                uploadSignature: (signature) => {
                    for (const image of images) {
                        image.src = signature.signatureImage;
                    }
                },
            },
            {
                onClose: () => {
                    snippetEl.remove();
                },
            }
        );
    }
}

registry
    .category("mass_mailing-plugins")
    .add(MassMailingSignatureSnippetPlugin.id, MassMailingSignatureSnippetPlugin);
