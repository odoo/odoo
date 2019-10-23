odoo.define('website_slides.course_content_manager', function (require) {
'use strict';

var core = require('web.core');
var QWeb = core.qweb;
var publicWidget = require('web.public.widget');
var websiteSlidesArchive = require('website_slides.slide.archive').websiteSlidesSlideArchive;
var websiteSlidesCategoryAdd = require('website_slides.category.add').websiteSlidesCategoryAdd;
var websiteSlidesCourseList = require('website_slides.course.slides.list');
var websiteSlidesTogglePreview = require('website_slides.slide.preview').websiteSlidesSlideToggleIsPreview;
var websiteSlidesUpload = require('website_slides.upload_modal').websiteSlidesUpload;

publicWidget.registry.websiteSlidesCourseContentManager = publicWidget.Widget.extend({
    selector: '.o_wslides_js_course_manager',
    custom_events: {
        'append_new_content': '_onAppendNewContent',
        'resequence_slides': '_onResequenceSlides',
        'archive_content': '_onArchiveContent'
    },

    start: function () {
        var self = this;
        this.dragAndDropWidget = new websiteSlidesCourseList(this, arguments);
        this._updateFullscreenHref();
        return this._super.apply(this, arguments).then(function () {
            return self._attachWidgetsToInitialContent();
        });
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /***
     * After appending new content to the dom, we have to instanciate and attach relevant widgets to them
     * so that they keep the same features as their siblings.
     *
     * On sections: Uploading new content
     * On slides: Archiving and Preview toggle
     *
     * @private
     */
    _attachWidgetsToAddedContent: function (categoryCreated) {
        var widgetPromises = [];
        widgetPromises.push(new websiteSlidesArchive(this, arguments).attachTo(this.$('.o_wslides_js_slide_archive.created-slide')));
        widgetPromises.push(new websiteSlidesTogglePreview(this, arguments).attachTo(this.$('.o_wslides_js_slide_toggle_is_preview.created-slide')));
        if (categoryCreated) {
            widgetPromises.push(new publicWidget.registry.websiteSlidesUpload(this, arguments).attachTo(this.$('.o_wslides_js_slide_upload.created-category')));
        }
        return Promise.all(widgetPromises);
    },

    /***
     * When the course homepage gets loaded, this method will attach every course content management related widgets
     * to their dom elements.
     *
     * Having them sharing the same parent allows us to trigger_up events when needed which in turn
     * help us avoid the usage of global dom selectors or duplicating code.
     *
     * Should new content management related widgets be added in the future, this is where they should be attached.
     * @private
     */
    _attachWidgetsToInitialContent: function () {
        var self = this;
        var widgetPromises = [];
        this.$('.o_wslides_js_slide_upload').map(function () {
            widgetPromises.push(new websiteSlidesUpload(self, arguments).attachTo($(this)));
        });
        this.$('.o_wslides_js_slide_section_add').map(function () {
            widgetPromises.push(new websiteSlidesCategoryAdd(self, arguments).attachTo($(this)));
        });
        this.$('.o_wslides_js_slide_archive').map(function () {
            widgetPromises.push(new websiteSlidesArchive(self, arguments).attachTo($(this)));
        });
        this.$('.o_wslides_js_slide_toggle_is_preview').map(function () {
            widgetPromises.push(new websiteSlidesTogglePreview(self, arguments).attachTo($(this)));
        });
        widgetPromises.push(this.dragAndDropWidget.attachTo(self.$('.o_wslides_slides_list')));
        return Promise.all(widgetPromises);
    },

    /**
     *
     * @param {*} categoryCreated
     * @param {*} categoryID
     */
    _getElementToAppendNewContentTo: function (categoryCreated, categoryID) {
        if (!categoryCreated) {
            return categoryID ? this.$('ul[data-category-id=' + categoryID + ']') : this.$('ul.o_wslides_slide_list').first();
        }
        return this.$('.o_wslides_js_slides_list_container');
    },

    /**
     * @private
     */
    _getSlides: function () {
        var slides = [];
        this.$('.o_wslides_js_list_item').each(function () {
            slides.push(parseInt($(this).data('slideId')));
        });
        return slides;
    },

    /**
     *
     * @param {*} data
     */
    _prepareNewContentValues: function (data) {
        this.slide = data.slide;
        this.channel = data.channel;
        this.category = data.category;
        this.category.slides = this.slide ? [this.slide] : [];
        this.modulesToInstallString = data.modulesToInstallString;
    },

    /**
     * @private
     */
    _updateEmptyFlags: function () {
        var categories = this.$('.o_wslides_slide_list');
        for (var i = 0; i < categories.length; i++) {
            var categoryID = $(categories[i]).data('categoryId');
            var categorySlideCount = $(categories[i]).find('.o_wslides_slides_list_slide:not(.o_not_editable)').length;
            if (categorySlideCount === 0) {
                this.$('.category-empty[data-category-id=' + categoryID + ']').removeClass('d-none');
            } else {
                this.$('.category-empty[data-category-id=' + categoryID + ']').addClass('d-none');
            }
        }
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
    _updateFullscreenHref: function () {
        this.$(".o_wslides_js_slides_list_slide_link").each(function () {
            var href = $(this).attr('href');
            var splittedHref = href.split('?');
            var search = splittedHref[1] || '';
            var searchParams = new URLSearchParams(search);
            searchParams.append("fullscreen", "1");
            $(this).attr('href', splittedHref[0] + '?' + searchParams.toString());
        });
    },
    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /***
     *
     * @private
     * @param {*} ev
     */
    _onAppendNewContent: function (ev) {
        var self = this;
        this._prepareNewContentValues(ev.data);
        var elementToAppendTo = this._getElementToAppendNewContentTo(ev.data.category_created, this.category.id);
        var template = ev.data.category_created ? 'website.slide.list.category.item' : 'website.slide.list.slide.item';
        elementToAppendTo.append(QWeb.render(template, {widget: this}));
        this._onResequenceSlides();
        this._attachWidgetsToAddedContent(ev.data.category_created).then(function () {
            self.dragAndDropWidget._bindSortable();
            self.$('.created-category').removeClass('created-category');
            self.$('.created-slide').removeClass('created-slide');
            ev.data.onSuccess();
        });
    },

    /***
     * @private
     * @param {*} ev
     */
    _onArchiveContent: function (ev) {
        this.$('.o_wslides_slides_list_slide[data-slide-id=' + ev.data.slideId + ']').remove();
        this._updateEmptyFlags();
        ev.data.onSuccess();
    },

    /**
     * This method must be called whenever a slide gets uploaded or a drag and drop happens !!!
     * @private
     */
    _onResequenceSlides: function () {
        var self = this;
        this._rpc({
            route: '/web/dataset/resequence',
            params: {
                model: "slide.slide",
                ids: self._getSlides()
            }
        }).then(function () {
            self._updateEmptyFlags();
        });
    }
});

});
