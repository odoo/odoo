$(document).ready(function () {
    $('a.js_update_line_json').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var href = $link.attr("href");
        var order_id = $link.attr("href").match(/order_id=([0-9]+)/);
        var line_id = href.match(/update_line\/([0-9]+)/);
        openerp.jsonRpc("/quote/update_line/", 'call', {
                'line_id': line_id[1],
                'order_id': parseInt(order_id[1]),
                'remove': $link.is('[href*="remove"]'),
                'unlink': $link.is('[href*="unlink"]')
                })
                .then(function (data) {
                    if(!data){
                        location.reload();
                    }
                    $link.parents('.input-group:first').find('.js_quantity').val(data[0]);
                    $('[data-id="total_amount"]>span').html(data[1]);
                });
        return false;
    });
});
//vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
