/** @odoo-module **/

import { BlockTab } from "@html_builder/sidebar/block_tab";
import { onMounted } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(BlockTab.prototype, {
    setup() {
        super.setup();

        this.websiteService = useService("website");

        onMounted(() => {
            this.handlePostInstall();
        });
    },

    /**
     * Handles the post-installation of a snippet module.
     * It will open the snippet dialog if a module was just installed,
     */
    async handlePostInstall() {
        if (
            this.websiteService.context.showNewContentModal ||
            !this.websiteService.context.newInstalledModule
        ) {
            return;
        }
        const snippetTitle = this.websiteService.context.newInstalledModule;
        if (snippetTitle) {
            this.websiteService.context.newInstalledModule = null;
            const snippet = this.getSnippetBySnippetTitle(snippetTitle);
            if (snippet.length) {
                this.onSnippetGroupClick(snippet[0]);
            }
        }
    },

    getSnippetBySnippetTitle(snippetTitle) {
        return this.snippetModel.snippetGroups.filter(
            (snippet) => snippet.title == snippetTitle
        );
    }
});
