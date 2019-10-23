odoo.define('website_slides.slide.archive', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var ajax = require('web.ajax');
var Dialog = require('web.Dialog');
var core = require('web.core');
var _t = core._t;

var SlideArchiveDialog = Dialog.extend({
    template: 'slides.slide.archive',

    /**
     * @override
     */
    init: function (parent, options) {
        options = _.defaults(options || {}, {
            title: _t('Archive Slide'),
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

        this.slideId = options.slideId;
        this._super(parent, options);
    },
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Calls 'archive' on slide controller and then visually removes the slide dom element
     */
    _onClickArchive: function () {
        var self = this;
        ajax.jsonRpc('/slides/slide/archive', 'call', {
            slide_id: this.slideId
        }).then(function (res) {
            if (!res.error) {
                self.trigger_up('archive_content', {slideId: self.slideId, onSuccess: self.close.bind(self)});
            }
        });
    }
});

publicWidget.registry.websiteSlidesSlideArchive = publicWidget.Widget.extend({
    xmlDependencies: ['/website_slides/static/src/xml/slide_management.xml'],
    events: {
        'click': '_onArchiveSlideClick',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _openDialog: function ($slideTarget) {
        new SlideArchiveDialog(this, {slideId: $slideTarget.data('slideId')}).open();
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
