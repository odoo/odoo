import { SnippetViewer } from "@html_builder/snippets/snippet_viewer";
import { markup, onMounted, onPatched, onWillPatch, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { Image } from "@html_builder/core/img";

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

    getPrefixIcons(snippetContentEl) {
        /** @type {PrefixIconInfo[]} */
        const icons = super.getPrefixIcons(snippetContentEl);
        const styleProps = { style: "height: 1em", attrs: { fill: "var(--body-color)" } };
        if (snippetContentEl.matches(".o_snippet_desktop_invisible")) {
            icons.push({
                keyClass: "o_prefix_desktop_invisible",
                title: "Invisible on desktop",
                Component: Image,
                props: {
                    src: "/html_builder/static/img/options/desktop_invisible.svg",
                    ...styleProps,
                },
            });
        }
        if (snippetContentEl.matches(".o_snippet_mobile_invisible")) {
            icons.push({
                keyClass: "o_prefix_mobile_invisible",
                title: "Invisible on mobile",
                Component: Image,
                props: {
                    src: "/html_builder/static/img/options/mobile_invisible.svg",
                    ...styleProps,
                },
            });
        }
        if (snippetContentEl.matches("[data-visibility=conditional]")) {
            icons.push({
                keyClass: "o_prefix_conditional",
                title: "Conditionally visible",
                content: markup`<span class="fa fa-eye-slash"/>`,
            });
        }
        return icons;
    },
});
