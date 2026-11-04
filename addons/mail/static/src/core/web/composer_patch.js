import { SIGNATURE_CLASS } from "@html_editor/main/signature_plugin";
import { wrapInlinesInBlocks } from "@html_editor/utils/dom";
import { childNodes } from "@html_editor/utils/dom_traversal";
import { parseHTML } from "@html_editor/utils/html";
import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { renderToElement } from "@web/core/utils/render";

patch(Composer.prototype, {
    /**
     * Construct an editor friendly html representation of the body.
     *
     * @param {string} defaultBody
     * @param {Markup} signature
     * @returns {string}
     */
    formatDefaultBodyForFullComposer(defaultBody, signature = "") {
        const fragment = parseHTML(document, defaultBody);
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
        return container.innerHTML;
    },
});
