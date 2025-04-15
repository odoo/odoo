/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";

options.registry.Showcase = options.Class.extend({
    /**
     * @override
     */
    onMove: function () {
        const $showcaseCol = this.$target.parent().closest('.row > div');
        const isLeftCol = $showcaseCol.index() <= 0;
        const $title = this.$target.children('.s_showcase_title');
        $title.toggleClass('flex-lg-row-reverse', isLeftCol);
        $showcaseCol.find('.s_showcase_icon.ms-3').removeClass('ms-3').addClass('ms-lg-3'); // For compatibility with old version
        $title.find('.s_showcase_icon').toggleClass('me-lg-0 ms-lg-3', isLeftCol);
    },
});
