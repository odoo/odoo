/** @odoo-module **/

    import publicWidget from '@web/legacy/js/public/public_widget';
    import { rpc } from "@web/core/network/rpc";

    publicWidget.registry.websiteSlidesSlideToggleIsPreview = publicWidget.Widget.extend({
        selector: '.o_wslides_js_slide_toggle_is_preview',
        events: {
            'click': '_onPreviewSlideClick',
        },

        _toggleSlidePreview: function(slideTarget) {
            rpc('/slides/slide/toggle_is_preview', {
                slide_id: slideTarget.dataset.slide_id,
            }).then(function (isPreview) {
                if (isPreview) {
                    slideTarget.classList.remove('text-bg-light badge-hide border');
                    slideTarget.classList.add('text-bg-success');
                } else {
                    slideTarget.classList.remove('text-bg-success');;
                    slideTarget.classList.add('text-bg-light badge-hide border');;
                }
            });
        },

        _onPreviewSlideClick: function (ev) {
            ev.preventDefault();
            this._toggleSlidePreview(ev.currentTarget);
        },
    });

    export default {
        websiteSlidesSlideToggleIsPreview: publicWidget.registry.websiteSlidesSlideToggleIsPreview
    };
