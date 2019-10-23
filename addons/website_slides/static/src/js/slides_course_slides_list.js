odoo.define('website_slides.course.slides.list', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var core = require('web.core');
var _t = core._t;

publicWidget.registry.websiteSlidesCourseSlidesList = publicWidget.Widget.extend({
    start: function () {
        this._super.apply(this,arguments);
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
            stop: this._resequenceSlides.bind(this),
            items: '.o_wslides_slide_list_category',
            placeholder: 'o_wslides_slides_list_slide_hilight position-relative mb-1'
        });

        this.$('.o_wslides_js_slides_list_container ul').sortable({
            handle: '.o_wslides_slides_list_drag',
            connectWith: '.o_wslides_js_slides_list_container ul',
            stop: this._resequenceSlides.bind(this),
            items: '.o_wslides_slides_list_slide:not(.o_wslides_js_slides_list_empty)',
            placeholder: 'o_wslides_slides_list_slide_hilight position-relative mb-1'
        });
    },
    _resequenceSlides: function (){
        this.trigger_up('resequence_slides');
    }
});

return publicWidget.registry.websiteSlidesCourseSlidesList;

});
