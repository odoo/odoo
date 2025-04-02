import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class WebsiteSlidesSort extends Interaction {
    static selector = ".o_wslides_slides_list";

    dynamicContent = {
        ...this.dynamicContent,
        ".o_wslides_slide_list_category_empty": {
            "t-att-class": (el) => ({ "d-none": !this.isCategoryEmpty(el) }),
        },
        ".o_wslides_js_slides_list_slide_link": {
            "t-att-href": (el) => `${el.href}${el.href.indexOf("?") !== -1 ? "&" : "?"}fullscreen=1`,
        },
    };

    setup() {
        super.setup();
        this.orm = this.services.orm;
        this.sortable = this.services.sortable;
        this.bindedSortable = [];
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
    isCategoryEmpty(el) {
        const categoryHeaderEl = el.closest(".o_wslides_slide_list_category");
        return (
            categoryHeaderEl?.querySelectorAll(".o_wslides_slides_list_slide:not(.o_not_editable)")
                .length == 0
        );
    }

    getSlides() {
        return [...this.el.querySelectorAll(".o_wslides_js_list_item")].map((el) =>
            parseInt(el.dataset.slideId)
        );
    }

    async reorderSlides() {
        await this.waitFor(this.orm.webResequence("slide.slide", this.getSlides()));
    }

}

registry.category("public.interactions").add("website_slides.WebsiteSlidesSort", WebsiteSlidesSort);
