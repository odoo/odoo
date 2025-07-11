import { SnippetViewer } from "@html_builder/snippets/snippet_viewer";
import { onMounted, onPatched, onWillPatch, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class WebsiteSnippetViewer extends SnippetViewer {
    setup() {
        super.setup();

        this.websiteService = useService("website");
        this.innerWebsiteEditService =
            this.websiteService.websiteRootInstance?.bindService("website_edit");
        this.previousSearch = "";

        const updatePreview = () => {
            if (this.innerWebsiteEditService) {
                this.innerWebsiteEditService.update(this.content.el, "preview");
            }
        };
        const stopPreview = () => {
            if (this.innerWebsiteEditService) {
                this.innerWebsiteEditService.stop(this.content.el);
            }
        };
        onMounted(updatePreview);
        onPatched(updatePreview);

        onWillPatch(stopPreview);
        onWillUnmount(stopPreview);
    }
}
