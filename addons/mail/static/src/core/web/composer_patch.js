import { SIGNATURE_CLASS } from "@html_editor/main/signature_plugin";
import { wrapInlinesInBlocks } from "@html_editor/utils/dom";
import { childNodes } from "@html_editor/utils/dom_traversal";

import { Composer } from "@mail/core/common/composer";
import { createDocumentFragmentFromContent } from "@mail/utils/common/html";

import { markup } from "@odoo/owl";

import { patch } from "@web/core/utils/patch";
import { renderToElement } from "@web/core/utils/render";

patch(Composer.prototype, {
    /**
     * Construct an editor friendly html representation of the body.
     *
     * @param {string|ReturnType<markup>} defaultBody
     * @param {string|ReturnType<markup>} [signature=""]
     * @returns {ReturnType<markup>}
     */
    formatDefaultBodyForFullComposer(defaultBody, signature = "") {
        const fragment = createDocumentFragmentFromContent(defaultBody).body;
        if (!fragment.firstChild) {
            fragment.append(document.createElement("BR"));
        }
        if (signature) {
            const signatureEl = renderToElement("html_editor.Signature", {
                signature,
                signatureClass: SIGNATURE_CLASS,
            });
            fragment.append(signatureEl);
        }
        const container = document.createElement("DIV");
        container.append(...childNodes(fragment));
        wrapInlinesInBlocks(container, { baseContainerNodeName: "DIV" });
        return markup(container.innerHTML);
    },
});
