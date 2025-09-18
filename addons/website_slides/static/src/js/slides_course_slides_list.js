import publicWidget from '@web/legacy/js/public/public_widget';
import { _t } from "@web/core/l10n/translation";
import { SlideCoursePage } from '@website_slides/js/slides_course_page';

publicWidget.registry.websiteSlidesCourseSlidesList = SlideCoursePage.extend({
    selector: '.o_wslides_slides_list',

    init: function () {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },

    start: function () {
        this._super.apply(this,arguments);

        this.channelId = this.el.dataset.channelId;
        this.bindedSortable = [];

        this._updateHref();
        this._bindSortable();
    },

    destroy() {
        this._unbindSortable();
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------,

    /**
     * Bind the sortable service to both
     * - course sections
     * - course slides
     *
     * @private
     */
    _bindSortable: function () {
        const sortableBaseParam = {
            clone: false,
            placeholderClasses: ['o_wslides_slides_list_slide_hilight', 'position-relative', 'mb-1'],
            onDrop: this._reorderSlides.bind(this),
            applyChangeOnDrop: true
        };

        const container = this.el.querySelector('ul.o_wslides_js_slides_list_container');
        this.bindedSortable.push(this.call(
            "sortable",
            "create",
            {
                ...sortableBaseParam,
                ref: { el: container },
                elements: ".o_wslides_slide_list_category",
                handle: ".o_wslides_slide_list_category_header .o_wslides_slides_list_drag",
                sortableId: "category",
            },
        ).enable());

        this.bindedSortable.push(this.call(
            "sortable",
            "create",
            {
                ...sortableBaseParam,
                ref: { el: container },
                elements: ".o_wslides_slides_list_slide:not(.o_wslides_js_slides_list_empty):not(.o_not_editable)",
                handle: ".o_wslides_slides_list_drag",
                connectGroups: true,
                groups: ".o_wslides_js_slides_list_container ul",
                sortableId: "list",
            },
        ).enable());
    },

    _unbindSortable: function () {
        this.bindedSortable.forEach(sortable => sortable.cleanup());
    },

    /**
     * This method will check that a section is empty/not empty
     * when the slides are reordered and show/hide the
     * "Empty category" placeholder.
     *
     * @private
     */
    _checkForEmptySections: function () {
        for (const category of this.el.querySelectorAll('.o_wslides_slide_list_category')) {
            const header = category.querySelector('.o_wslides_slide_list_category_header');
            const slideCount = category.querySelectorAll('.o_wslides_slides_list_slide:not(.o_not_editable)').length;
            const flagContainer = header.querySelector('.o_wslides_slides_list_drag');
            const emptyFlag = flagContainer?.querySelector('small');
            if (slideCount === 0 && !emptyFlag) {
                const small = document.createElement('small');
                small.className = 'ms-1 text-muted fw-bold';
                small.textContent = _t("(empty)");
                flagContainer.appendChild(small);
            } else if (slideCount > 0 && emptyFlag) {
                emptyFlag.remove();
            }
        }
    },

    /**
     * Collects all slide IDs in their current DOM order.
     *
     * @private
     * @returns {number[]}
     */
    _getSlides: function () {
        var categories = [];
        for (const el of this.el.querySelectorAll('.o_wslides_js_list_item')) {
            categories.push(parseInt(el.dataset.slideId));
        }
        return categories;
    },

    _reorderSlides: function () {
        var self = this;
        this.orm
            .webResequence("slide.slide", this._getSlides())
            .then(function (res) {
                self._checkForEmptySections();
            });
    },

    /**
     * Change links href to fullscreen mode for SEO.
     *
     * Specifications demand that links are generated (xml) without the "fullscreen"
     * parameter for SEO purposes.
     *
     * This method then adds the parameter as soon as the page is loaded.
     *
     * @private
     */
    _updateHref: function () {
        for (const link of this.el.querySelectorAll(".o_wslides_js_slides_list_slide_link")) {
            const href = link.getAttribute('href');
            const operator = href.indexOf('?') !== -1 ? '&' : '?';
            link.setAttribute('href', href + operator + "fullscreen=1");
        }
    }
});

export default publicWidget.registry.websiteSlidesCourseSlidesList;
