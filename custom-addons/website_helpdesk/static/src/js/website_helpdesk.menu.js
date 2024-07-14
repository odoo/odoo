/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.HelpdeskMenu = publicWidget.Widget.extend({
    selector: '.team_menu',

    /**
     * @override
     */
    start: function () {
        var pathname = $(window.location).attr("pathname");
        var $links = this.$('li a');
        if (pathname !== "/helpdesk") {
            $links = $links.filter("[href$='" + pathname + "']");
        }
        $links.first().closest("li").addClass("active");

        return this._super.apply(this, arguments);
    },
});
