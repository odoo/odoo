import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { parseHTML } from "@html_editor/utils/html";
import { user } from "@web/core/user";
import { withSequence } from "@html_editor/utils/resource";
import { renderToString } from "@web/core/utils/render";
import { markup } from "@odoo/owl";
import { isEmptyBlock, paragraphRelatedElementsSelector } from "@html_editor/utils/dom_info";

export const SIGNATURE_CLASS = "o-signature-container";

export class SignaturePlugin extends Plugin {
    static id = "signature";
    static dependencies = ["dom", "history", "selection"];
    static shared = ["cleanSignatures"];
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
        is_empty_predicates: this.isEmpty.bind(this),
        unsplittable_node_predicates: (host) =>
            host.nodeType === Node.ELEMENT_NODE && host.matches(`.${SIGNATURE_CLASS}`),
    };

    cleanSignatures({ rootClone }) {
        for (const el of rootClone.querySelectorAll(`.${SIGNATURE_CLASS}`)) {
            el.remove();
        }
    }

    async insertSignature() {
        const [currentUser] = await this.services.orm.read(
            "res.users",
            [user.userId],
            ["signature"]
        );
        if (currentUser && currentUser.signature) {
            // User signature is sanitized in backend.
            const signatureFragment = parseHTML(
                this.document,
                renderToString("html_editor.Signature", {
                    signature: markup(currentUser.signature),
                    signatureClass: SIGNATURE_CLASS,
                })
            );
            const signatureBlock = signatureFragment.firstElementChild;
            this.dependencies.dom.insert(signatureFragment);
            if (signatureBlock) {
                const lastPhrasingElement = [
                    ...signatureBlock.querySelectorAll(paragraphRelatedElementsSelector),
                ].at(-1);
                if (lastPhrasingElement) {
                    this.dependencies.selection.setCursorEnd(lastPhrasingElement);
                } else {
                    this.dependencies.selection.setCursorEnd(signatureBlock);
                }
            }
            this.dependencies.history.addStep();
        }
    }

    isEmpty(element) {
        if (
            element.nodeType === Node.ELEMENT_NODE &&
            element.matches(`.${SIGNATURE_CLASS}`) &&
            isEmptyBlock(element)
        ) {
            return true;
        }
    }
}
