/** @odoo-module **/

import { Component } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.AboutSection = publicWidget.Widget.extend({
    selector: '.section-about, .section-about-content, .section-our-main-service',

    events: {
        'click .read-more-toggle': '_onToggleReadMore',
    },

    start: function () {
        // Select all read more toggles and additional services within this section
        this.$readMoreToggles = this.$('.read-more-toggle');
        this.$additionalServices = this.$('.additional-services');
        this.$readMoreTexts = this.$('.read-more-text');

        return this._super.apply(this, arguments);
    },

    _onToggleReadMore: function (ev) {
        ev.preventDefault();

        // Find the closest additional services div and read more text
        const $toggle = $(ev.currentTarget);
        const $additionalServices = $toggle.siblings('.additional-services');
        const $readMoreText = $toggle.find('.read-more-text');

        // Toggle visibility
        if ($additionalServices.css('display') === 'none') {
            $additionalServices.css('display', 'block');
            $readMoreText.text('\u00A0\u00A0Read less\u00A0\u00A0   - \u00A0\u00A0');
        } else {
            $additionalServices.css('display', 'none');
            $readMoreText.text('\u00A0\u00A0Read more\u00A0\u00A0   +\u00A0\u00A0');
        }
    },
});

export default publicWidget.registry.AboutSection;