odoo.define('show_duplicated_post_option', function (require) {

    "use strict";

    // var base = require('web_editor.base');
    require('web.dom_ready');


    $('select.select_reason').change(function () {
        var $el = $(this);
        // var $visiblity_choose_duplicate_post = $el.closest('div').find('.hide_until_duplicate');
        var $visiblity_choose_duplicate_post = $('.hide_until_duplicate');

        var show = $el.find("option:selected").attr('duplicated-option') === "True";
        $visiblity_choose_duplicate_post.toggleClass('visible', show).toggleClass('invisible', !show);
    });

});