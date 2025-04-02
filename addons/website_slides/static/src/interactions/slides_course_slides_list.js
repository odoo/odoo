import { registry } from "@web/core/registry";
import { WebsiteSlidesCoursePage } from "./slides_course_page";
import { _t } from "@web/core/l10n/translation";

class WebsiteSlidesCourseSlidesList extends WebsiteSlidesCoursePage {
    static selector = ".o_wslides_slides_list";

    setup() {
        super.setup();
        this.orm = this.services.orm;
        this.sortable = this.services.sortable;
        this.channelId = Number(this.el.dataset.channelId);
        this.bindedSortable = [];
        this.updateHref();
        this.bindSortable();
    }

    destroy() {
        this.unbindSortable();
    }

    bindSortable() {
        const sortableBaseParam = {
            clone: false,
            placeholderClasses: [
                "o_wslides_slides_list_slide_hilight",
                "position-relative",
                "mb-1",
            ],
            onDrop: this.reorderSlides.bind(this),
            applyChangeOnDrop: true,
        };
        const containerEl = this.el.querySelector("ul.o_wslides_js_slides_list_container");
        this.bindedSortable.push(
            this.sortable
                .create({
                    ...sortableBaseParam,
                    ref: { el: containerEl },
                    elements: ".o_wslides_slide_list_category",
                    handle: ".o_wslides_slide_list_category_header .o_wslides_slides_list_drag",
                    sortableId: "category",
                })
                .enable()
        );

        this.bindedSortable.push(
            this.sortable
                .create({
                    ...sortableBaseParam,
                    ref: { el: containerEl },
                    elements:
                        ".o_wslides_slides_list_slide:not(.o_wslides_js_slides_list_empty):not(.o_not_editable)",
                    handle: ".o_wslides_slides_list_drag",
                    connectGroups: true,
                    groups: ".o_wslides_js_slides_list_container ul",
                    sortableId: "list",
                })
                .enable()
        );
    }

    unbindSortable() {
        for (const sortable of this.bindedSortable) {
            sortable.cleanup();
        }
    }

    /**
     * This method will check that a section is empty/not empty
     * when the slides are reordered and show/hide the
     * "Empty category" placeholder.
     */
    checkForEmptySections() {
        for (const el of this.el.querySelectorAll(".o_wslides_slide_list_category")) {
            const categoryHeaderEl = el.querySelector(".o_wslides_slide_list_category_header");
            const categorySlideCount = el.querySelectorAll(
                ".o_wslides_slides_list_slide:not(.o_not_editable)"
            ).length;
            const emptyFlagContainerEl = categoryHeaderEl.querySelector(
                ".o_wslides_slides_list_drag"
            );
            const emptyFlagEl = emptyFlagContainerEl.querySelector("small");
            if (categorySlideCount === 0 && !emptyFlagEl) {
                const smallEl = document.createElement("small");
                smallEl.classList.add("ms-1", "text-muted", "fw-bold");
                smallEl.textContent = _t("(empty)");
                this.insert(smallEl, emptyFlagContainerEl);
            } else if (categorySlideCount > 0 && emptyFlagEl) {
                emptyFlagEl.remove();
            }
        }
    }

    getSlides() {
        const categories = [];
        for (const el of this.el.querySelectorAll(".o_wslides_js_list_item")) {
            categories.push(parseInt(el.dataset.slideId));
        }
        return categories;
    }

    async reorderSlides() {
        await this.waitFor(this.orm.webResequence("slide.slide", this.getSlides()));
        this.checkForEmptySections();
    }

    /**
     * Change links href to fullscreen mode for SEO.
     *
     * Specifications demand that links are generated (xml) without the "fullscreen"
     * parameter for SEO purposes.
     *
     * This method then adds the parameter as soon as the page is loaded.
     */
    updateHref() {
        for (const el of this.el.querySelectorAll(".o_wslides_js_slides_list_slide_link")) {
            const href = el.href;
            const operator = href.indexOf("?") !== -1 ? "&" : "?";
            el.href = href + operator + "fullscreen=1";
        }
    }
}

registry
    .category("public.interactions")
    .add("website_slides.WebsiteSlidesCourseSlidesList", WebsiteSlidesCourseSlidesList);
