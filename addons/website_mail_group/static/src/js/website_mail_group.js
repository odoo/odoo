$(document).ready(function () {

    $('.o_mg_link_hide').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var $container = $link.parents('div').first();
        $container.find('.o_mg_link_hide').first().hide();
        $container.find('.o_mg_link_show').first().show();
        $container.find('.o_mg_link_content').first().show();
        return false;
    });

    $('.o_mg_link_show').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var $container = $link.parents('div').first();
        $container.find('.o_mg_link_hide').first().show();
        $container.find('.o_mg_link_show').first().hide();
        $container.find('.o_mg_link_content').first().hide();
        return false;
    });

    $('body').on('click', 'button.o_mg_read_more', function (ev) {
        var $link = $(ev.target);
        return openerp.jsonRpc($link.data('href'), 'call', {
            'last_displayed_id': $link.data('msg-id'),
        }).then(function (data) {
            if (! data) {
                return true;
            }
            var $current_ul = $link.parents('.o_mg_replies').first().find('ul.media-list');
            if ($current_ul) {
                $(data).find('li.media').insertAfter($current_ul.find('li.media').last());
                $(data).find('p.well').appendTo($current_ul);
            }
            var $show_more = $link.parents('p.well').first();
            $show_more.remove();
            return true;
        });
    });
});