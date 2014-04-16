$(document).ready(function () {

    $('.post_toc').change(function (ev) {
        var $option = $(ev.currentTarget);
        openerp.jsonRpc("/forum/question/toc", 'call', {
            'post_id' : $('#question').attr("value"),
            'toc_id': $option.attr("value"),
            })
        return true;
    });

});
