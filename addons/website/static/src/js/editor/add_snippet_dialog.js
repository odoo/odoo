import { AddSnippetDialog } from "@web_editor/js/editor/add_snippet_dialog";
import { patch } from "@web/core/utils/patch";
import { applyTextHighlight } from "@website/js/text_processing";
import { useService } from "@web/core/utils/hooks";
import { onWillUnmount } from "@odoo/owl";

patch(AddSnippetDialog.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup();

        this.websiteService = useService("website");
        this.websiteEditService =
            this.websiteService.websiteRootInstance.bindService("website_edit");

        onWillUnmount(() => {
            this.websiteEditService.stopInteractions(this.iframeDocument.body);
        });
    },

    /**
     * @override
     */
    async insertSnippets() {
        await super.insertSnippets();

        // Start preview interactions
        this.websiteEditService.update(this.iframeDocument.body, "preview");
    },

    /**
     * @override
     */
    _updateSnippetContent(targetEl) {
        super._updateSnippetContent(...arguments);
        // Build the highlighted text content for the snippets.
        for (const textEl of targetEl?.querySelectorAll(".o_text_highlight") || []) {
            applyTextHighlight(textEl);
        }
    },
});
