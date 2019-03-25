odoo.define('website_slides.course.slides.list', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.websiteSlidesCourseSlidesList = publicWidget.Widget.extend({
    selector: '.o_wslides_slides_list',
    xmlDependencies: ['/website_slides/static/src/xml/website_slides_upload.xml'],

    start: function () {
        this._super.apply(this,arguments);

        this.channelId = this.$el.data('channelId');

        this._updateHref();
        this._bindSortable();
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
        this.$('ul.o_wslides_js_slides_list_container').sortable({
            handle: '.o_wslides_slides_list_drag',
            stop: this._reorderCategories.bind(this),
            items: '.o_wslides_slide_list_category',
            placeholder: 'o_wslides_slides_list_slide_hilight position-relative mb-1'
        });

        this.$('.o_wslides_js_slides_list_container ul').sortable({
            handle: '.o_wslides_slides_list_drag',
            connectWith: '.o_wslides_js_slides_list_container ul',
            stop: this._reorderSlides.bind(this),
            items: '.o_wslides_slides_list_slide:not(.o_wslides_js_slides_list_empty)',
            placeholder: 'o_wslides_slides_list_slide_hilight position-relative mb-1'
        });
    },

    /**
     * This method will check that a section is empty/not empty
     * when the slides are reordered and show/hide the
     * "Empty category" placeholder.
     *
     * @private
     */
    _checkForEmptySections: function (){
        this.$('.o_wslides_js_slides_list_container ul').each(function (){
            var $emptyCategory = $(this).find('.o_wslides_js_slides_list_empty');
            if ($(this).find('li.o_wslides_slides_list_slide[data-slide-id]').length === 0) {
                $emptyCategory.removeClass('d-none').addClass('d-flex');
            } else {
                $emptyCategory.addClass('d-none').removeClass('d-flex');
            }
        });
    },

    _getCategories: function (){
        var categories = [];
        this.$('.o_wslides_js_category').each(function (){
            categories.push(parseInt($(this).data('categoryId')));
        });
        return categories;
    },

    /**
     * Returns a slides dict in the form:
     * {slide_id: {'sequence': slide_sequence, 'category_id': slide.category_id.id}}
     *
     *
     * (Uncategorized slides don't have the category_id key)
     *
     * @private
     */
    _getSlides: function (){
        var slides = {};
        this.$('li.o_wslides_slides_list_slide[data-slide-id]').each(function (index){
            var $slide = $(this);
            var values = {
                sequence: index
            };

            var categoryId = $slide.closest('.o_wslides_slide_list_category').data('categoryId');
            if (typeof categoryId !== typeof undefined && categoryId !== false) {
                values.category_id = categoryId;
            }

            slides[$slide.data('slideId')] = values;
        });

        return slides;
    },

    _reorderCategories: function (){
        var self = this;
        self._rpc({
            route: '/web/dataset/resequence',
            params: {
                model: "slide.category",
                ids: self._getCategories()
            }
        });
    },

    _reorderSlides: function (){
        this._checkForEmptySections();

        this._rpc({
            route: "/slides/channel/resequence",
            params: {
                channel_id: this.channelId,
                slides_data: this._getSlides()
            }
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

return publicWidget.registry.websiteSlidesCourseSlidesList;

});
