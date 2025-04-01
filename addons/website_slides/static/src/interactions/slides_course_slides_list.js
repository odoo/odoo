import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";
import { SlideCoursePage } from "@website_slides/interactions/slides_course_page";

publicWidget.registry.websiteSlidesCourseSlidesList = SlideCoursePage.extend({
    selector: ".o_wslides_slides_list",

    init: function () {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },

    start: function () {
        this._super.apply(this, arguments);

        this.channelId = this.$el.data("channelId");
        this.bindedSortable = [];

        this.updateHref();
        this.bindSortable();
    },

    destroy() {
        this.unbindSortable();
        return this._super(...arguments);
    },

    /**
     * Bind the sortable jQuery widget to both
     * - course sections
     * - course slides
     */
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
            this.call("sortable", "create", {
                ...sortableBaseParam,
                ref: { el: containerEl },
                elements: ".o_wslides_slide_list_category",
                handle: ".o_wslides_slide_list_category_header .o_wslides_slides_list_drag",
                sortableId: "category",
            }).enable()
        );

        this.bindedSortable.push(
            this.call("sortable", "create", {
                ...sortableBaseParam,
                ref: { el: containerEl },
                elements:
                    ".o_wslides_slides_list_slide:not(.o_wslides_js_slides_list_empty):not(.o_not_editable)",
                handle: ".o_wslides_slides_list_drag",
                connectGroups: true,
                groups: ".o_wslides_js_slides_list_container ul",
                sortableId: "list",
            }).enable()
        );
    },

    unbindSortable() {
        for (const sortable of this.bindedSortable) {
            sortable.cleanup();
        }
    },

    /**
     * This method will check that a section is empty/not empty
     * when the slides are reordered and show/hide the
     * "Empty category" placeholder.
     */
    checkForEmptySections() {
        this.$(".o_wslides_slide_list_category").each(function () {
            var $categoryHeader = $(this).find(".o_wslides_slide_list_category_header");
            var categorySlideCount = $(this).find(
                ".o_wslides_slides_list_slide:not(.o_not_editable)"
            ).length;
            var $emptyFlagContainer = $categoryHeader.find(".o_wslides_slides_list_drag").first();
            var $emptyFlag = $emptyFlagContainer.find("small");
            if (categorySlideCount === 0 && $emptyFlag.length === 0) {
                $emptyFlagContainer.append(
                    $("<small>", {
                        class: "ms-1 text-muted fw-bold",
                        text: _t("(empty)"),
                    })
                );
            } else if (categorySlideCount > 0 && $emptyFlag.length > 0) {
                $emptyFlag.remove();
            }
        });
    },

    getSlides() {
        const categories = [];
        for (const el of this.el.querySelectorAll(".o_wslides_js_list_item")) {
            categories.push(parseInt(el.dataset.slideId));
        }
        return categories;
    },
    async reorderSlides() {
        await this.orm.webResequence("slide.slide", this.getSlides());
        this.checkForEmptySections();
    },

    /**
     * Change links href to fullscreen mode for SEO.
     *
     * Specifications demand that links are generated (xml) without the "fullscreen"
     * parameter for SEO purposes.
     *
     * This method then adds the parameter as soon as the page is loaded.
     */
    updateHref() {
        this.$(".o_wslides_js_slides_list_slide_link").each(function () {
            var href = $(this).attr("href");
            var operator = href.indexOf("?") !== -1 ? "&" : "?";
            $(this).attr("href", href + operator + "fullscreen=1");
        });
    },
});

export default publicWidget.registry.websiteSlidesCourseSlidesList;
