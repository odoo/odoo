/** @odoo-module **/

import dom from "@web/legacy/js/core/dom";
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.miniNavbarScroll = publicWidget.Widget.extend({
    selector: '.s_mini_nav_bar a[href*="#"]:not([href="#"])',
    events: {
        'click': '_onClick',
    },

    //----------------------------------------------------------------------
    // Handlers
    //----------------------------------------------------------------------

    /**
     * Called on click on the mini navbar link -> scroll to the section.
     *
     * @private
     */
    _onClick: function (ev) {
        var index = $(this).parent().index();
        var target = $('.o_scroll_nav').get(index);
        if (target) {
            ev.preventDefault();
            dom.scrollTo(target);
        }
    },
});
