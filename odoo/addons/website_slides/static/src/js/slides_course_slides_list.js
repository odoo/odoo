/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { _t } from "@web/core/l10n/translation";
import { SlideCoursePage } from '@website_slides/js/slides_course_page';

publicWidget.registry.websiteSlidesCourseSlidesList = SlideCoursePage.extend({
    selector: '.o_wslides_slides_list',

    start: function () {
        this._super.apply(this,arguments);

        this.channelId = this.$el.data('channelId');
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
     * Bind the sortable jQuery widget to both
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
    _checkForEmptySections: function (){
        this.$('.o_wslides_slide_list_category').each(function (){
            var $categoryHeader = $(this).find('.o_wslides_slide_list_category_header');
            var categorySlideCount = $(this).find('.o_wslides_slides_list_slide:not(.o_not_editable)').length;
            var $emptyFlagContainer = $categoryHeader.find('.o_wslides_slides_list_drag').first();
            var $emptyFlag = $emptyFlagContainer.find('small');
            if (categorySlideCount === 0 && $emptyFlag.length === 0){
                $emptyFlagContainer.append($('<small>', {
                    'class': "ms-1 text-muted fw-bold",
                    text: _t("(empty)")
                }));
            } else if (categorySlideCount > 0 && $emptyFlag.length > 0){
                $emptyFlag.remove();
            }
        });
    },

    _getSlides: function (){
        var categories = [];
        this.$('.o_wslides_js_list_item').each(function (){
            categories.push(parseInt($(this).data('slideId')));
        });
        return categories;
    },
    _reorderSlides: function (){
        var self = this;
        self.rpc('/web/dataset/resequence', {
            model: "slide.slide",
            ids: self._getSlides(),
        }).then(function (res) {
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
        this.$(".o_wslides_js_slides_list_slide_link").each(function (){
            var href = $(this).attr('href');
            var operator = href.indexOf('?') !== -1 ? '&' : '?';
            $(this).attr('href', href + operator + "fullscreen=1");
        });
    }
});

export default publicWidget.registry.websiteSlidesCourseSlidesList;
