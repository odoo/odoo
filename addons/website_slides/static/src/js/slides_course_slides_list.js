odoo.define('website_slides.slideslist', function (require) {
'use strict';

var sAnimations = require('website.content.snippets.animation');

sAnimations.registry.websiteSlidesCourseSlidesList = sAnimations.Class.extend({
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
        this.$('ul.o_wslides_slides_list_container').sortable({
            handle: '.fa-arrows',
            stop: this._reorderCategories.bind(this)
        });

        this.$('.o_wslides_slides_list_container ul').sortable({
            handle: '.fa-arrows',
            connectWith: '.o_wslides_slides_list_container ul',
            stop: this._reorderSlides.bind(this),
            items: '.o_wslides_slides_list_slide'
        });
    },

    _getCategories: function (){
        var categories = [];
        this.$('.o_wslides_slide_list_category_container').each(function (){
            categories.push(parseInt($(this).attr('category_id')));
        });

        return categories;
    },

    /**
     * Returns a slides dict in the form:
     * {slide_id: {'sequence': slide_sequence, 'category_id': slide.category_id.id}}
     *
     * @private
     */
    _getSlides: function (){
        var slides = {};
        this.$('li.o_wslides_slides_list_slide').each(function (index){
            var $slide = $(this);
            slides[$slide.attr('slide_id')] = {
                category_id: parseInt(
                    $slide.closest('.o_wslides_slide_list_category').attr('category_id')
                ),
                sequence: index
            };
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
        }).then(function (){
            self._resetCategoriesIndex();
        });
    },

    _reorderSlides: function (){
        this._rpc({
            route: "/slides/channel/resequence",
            params: {
                channel_id: this.channelId,
                slides_data: this._getSlides()
            }
        });
    },

    /**
     * Used to reset the categories numbering (1, 2, 3, ...) in the UI
     */
    _resetCategoriesIndex: function (){
        this.$('.section-index').each(function (index){
            $(this).text(index + 1);
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
        this.$(".o_wslides_slides_list_slide_link").each(function (){
            var href = $(this).attr('href');
            var operator = href.indexOf('?') !== -1 ? '&' : '?';
            $(this).attr('href', href + operator + "fullscreen=1");
        });
    }
});

return sAnimations.registry.websiteSlidesCourseSlidesList;

});