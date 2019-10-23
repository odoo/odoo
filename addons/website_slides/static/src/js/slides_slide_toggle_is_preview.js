odoo.define('website_slides.slide.preview', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var ajax = require('web.ajax');

    publicWidget.registry.websiteSlidesSlideToggleIsPreview = publicWidget.Widget.extend({
        events: {
            'click': '_onPreviewSlideClick',
        },

        _toggleSlidePreview: function ($slideTarget) {
            ajax.jsonRpc('/slides/slide/toggle_is_preview', 'call', {
                slide_id: $slideTarget.data('slideId')
            }).then(function (isPreview) {
                if (isPreview) {
                    $slideTarget.removeClass('badge-light badge-hide border');
                    $slideTarget.addClass('badge-success py-1');
                } else {
                    $slideTarget.removeClass('badge-success py-1');
                    $slideTarget.addClass('badge-light badge-hide border');
                }
            });
        },

        _onPreviewSlideClick: function (ev) {
            ev.preventDefault();
            this._toggleSlidePreview($(ev.currentTarget));
        },
    });

    return {
        websiteSlidesSlideToggleIsPreview: publicWidget.registry.websiteSlidesSlideToggleIsPreview
    };

});
