odoo.define('website_slides.slide.archive', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var Dialog = require('web.Dialog');
var core = require('web.core');
var _t = core._t;

var SlideArchiveDialog = Dialog.extend({
    template: 'slides.slide.archive',

    /**
     * @override
     */
    init: function (parent, options) {

        const dialogTitle = options.slideTarget.is('.o_wslides_js_category_archive') ? _t('Archive Category') : _t('Archive Slide');
        options = _.defaults(options || {}, {
            title: dialogTitle,
            size: 'medium',
            buttons: [{
                text: _t('Archive'),
                classes: 'btn-primary',
                click: this._onClickArchive.bind(this)
            }, {
                text: _t('Cancel'),
                close: true
            }]
        });

        this.$slideTarget = options.slideTarget;
        this.slideId = this.$slideTarget.data('slideId') || false;
        this.categoryId = this.$slideTarget.data('categoryId') || false;
        this._super(parent, options);
    },
    _checkForEmptySections: function (){
        $('.o_wslides_slide_list_category').each(function (){
            var $categoryHeader = $(this).find('.o_wslides_slide_list_category_header');
            var categorySlideCount = $(this).find('.o_wslides_slides_list_slide:not(.o_not_editable)').length;
            var $emptyFlagContainer = $categoryHeader.find('.o_wslides_slides_list_drag').first();
            var $emptyFlag = $emptyFlagContainer.find('small');
            if (categorySlideCount === 0 && $emptyFlag.length === 0){
                $emptyFlagContainer.append($('<small>', {
                    'class': "ml-1 text-muted font-weight-bold",
                    text: _t("(empty)")
                }));
            }
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Calls 'archive' on slide controller and then visually removes the slide dom element
     * (or in case of category, reloads the page after re-sequencing slides)
     */
    _onClickArchive: function () {
        const self = this;
        const isCategory = this.categoryId || false;
        let rpcParams;
        if (isCategory) {
            rpcParams = {
                route: '/slides/category/archive',
                params: {category_id: this.categoryId}
            };
        } else {
            rpcParams = {
                route: '/slides/slide/archive',
                params: {slide_id: this.slideId},
            };
        }

        this._rpc(rpcParams).then(function (isArchived) {
            if (isCategory) {
                    window.location.reload();
            } else if (isArchived){
                self.$slideTarget.closest('.o_wslides_slides_list_slide').remove();
                self._checkForEmptySections();
            }
            self.close();
        });
    }
});

publicWidget.registry.websiteSlidesSlideArchive = publicWidget.Widget.extend({
    selector: '.o_wslides_js_slide_archive, .o_wslides_js_category_archive',
    xmlDependencies: ['/website_slides/static/src/xml/slide_management.xml'],
    events: {
        'click': '_onArchiveSlideClick',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _openDialog: function ($slideTarget) {
        new SlideArchiveDialog(this, {slideTarget: $slideTarget}).open();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onArchiveSlideClick: function (ev) {
        ev.preventDefault();
        var $slideTarget = $(ev.currentTarget);
        this._openDialog($slideTarget);
    },
});

return {
    slideArchiveDialog: SlideArchiveDialog,
    websiteSlidesSlideArchive: publicWidget.registry.websiteSlidesSlideArchive
};

});
