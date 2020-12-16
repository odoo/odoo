odoo.define('website.s_showcase_options', function (require) {
'use strict';

const snippetOptions = require('web_editor.snippets.options');

snippetOptions.registry.Showcase = snippetOptions.SnippetOptionWidget.extend({
    /**
     * @override
     */
    onMove: function () {
        const $showcaseCol = this.$target.parent().closest('.row > div');
        const isLeftCol = $showcaseCol.index() <= 0;
        const $title = this.$target.children('.s_showcase_title');
        $title.toggleClass('flex-lg-row-reverse', isLeftCol);
        $showcaseCol.find('.s_showcase_icon.ml-3').removeClass('ml-3').addClass('ml-lg-3'); // For compatibility with old version
        $title.find('.s_showcase_icon').toggleClass('mr-lg-0 ml-lg-3', isLeftCol);
    },
});
});
