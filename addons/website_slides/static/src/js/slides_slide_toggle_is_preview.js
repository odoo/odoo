/** @odoo-module **/

    import publicWidget from 'web.public.widget';

    publicWidget.registry.websiteSlidesSlideToggleIsPreview = publicWidget.Widget.extend({
        selector: '.o_wslides_js_slide_toggle_is_preview',
        events: {
            'click': '_onPreviewSlideClick',
        },

        _toggleSlidePreview: function($slideTarget) {
            this._rpc({
                route: '/slides/slide/toggle_is_preview',
                params: {
                    slide_id: $slideTarget.data('slideId')
                },
            }).then(function (isPreview) {
                if (isPreview) {
                    $slideTarget.removeClass('bg-light bg-hide border');
                    $slideTarget.addClass('bg-success');
                } else {
                    $slideTarget.removeClass('bg-success');
                    $slideTarget.addClass('bg-light bg-hide border');
                }
            });
        },

        _onPreviewSlideClick: function (ev) {
            ev.preventDefault();
            this._toggleSlidePreview($(ev.currentTarget));
        },
    });

    export default {
        websiteSlidesSlideToggleIsPreview: publicWidget.registry.websiteSlidesSlideToggleIsPreview
    };
