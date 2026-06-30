import { SnippetViewer } from "@html_builder/snippets/snippet_viewer";
import { onMounted, onPatched, onWillPatch, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(SnippetViewer.prototype, {
    setup() {
        super.setup();

        if (this.props.snippetModel.snippetsName === "website.snippets") {
            this.websiteService = useService("website");
            this.innerWebsiteEditService =
                this.websiteService.websiteRootInstance?.env.services["website_edit"];
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
    },
    getContent(snippetEl) {
        let contentEl = snippetEl;
        if (this.props.snippetModel.snippetsName === "website.snippets") {
            const rfsEls = snippetEl.querySelectorAll(".o_rfs");
            if ([...rfsEls].some((rfsEl) => rfsEl.style.fontSize?.startsWith("clamp("))) {
                // Text toolbar responsive sizes use `clamp()` with `vw`.
                // Here, `vw` uses the full preview iframe width.
                // Column previews would otherwise render too large.
                // Adjust only the clone, keeping dropped content intact.
                contentEl = snippetEl.cloneNode(true);
                const snippetPreviewColumnCount = 2;
                for (const rfsEl of contentEl.querySelectorAll(".o_rfs")) {
                    if (rfsEl.style.fontSize?.startsWith("clamp(")) {
                        rfsEl.style.fontSize = rfsEl.style.fontSize.replace(
                            /([+-]?\d*\.?\d+)vw/g,
                            (_, value) => `${parseFloat(value) / snippetPreviewColumnCount}vw`
                        );
                    }
                }
            }
        }
        return super.getContent(contentEl);
    },
});
