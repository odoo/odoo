$(document).ready(function () {
    $('a.js_update_line_json').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var href = $link.attr("href");
        var qty = $link.attr("href").match(/qty=([0-9]+)/);
        var line_id = href.match(/update_line\/([0-9]+)/);
        console.log(line_id);
        openerp.jsonRpc("/quote/update_line/", 'call', {
                'line_id': line_id[1],
                'qty': qty[1],
                'remove': $link.is('[href*="remove"]'),
                'unlink': $link.is('[href*="unlink"]'),
                })
                .then(function (data) {
                    location.reload();
//                    $link.parent('.input-group:first').find('.js_line_qty').val(data[0]);
//                    $('[data-oe-model="sale.order"][data-oe-field="amount_total"]').replaceWith(data[1]);
                });
        return false;
    });
});
//vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
