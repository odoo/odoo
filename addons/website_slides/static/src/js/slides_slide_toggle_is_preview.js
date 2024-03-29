/** @odoo-module **/

    import publicWidget from '@web/legacy/js/public/public_widget';

    publicWidget.registry.websiteSlidesSlideToggleIsPreview = publicWidget.Widget.extend({
        selector: '.o_wslides_js_slide_toggle_is_preview',
        events: {
            'click': '_onPreviewSlideClick',
        },

        init() {
            this._super(...arguments);
            this.rpc = this.bindService("rpc");
        },

        _toggleSlidePreview: function($slideTarget) {
            this.rpc('/slides/slide/toggle_is_preview', {
                slide_id: $slideTarget.data('slideId')
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
