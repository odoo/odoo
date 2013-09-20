$(function () {
    $(document).on('click', '.js_publish', function (e) {
        var id = $(this).data('id');
        var loadpublish = function () {
            return openerp.jsonRpc('/recruitment/published', 'call', {'id': id});
        }
        var i = 0;
        $(this).ajaxComplete(function(el, xhr, settings) {
            if (settings.url == "/website/publish") {
                i++;
                if (i == 1)
                    settings.jsonpCallback = loadpublish()
            }
        });
    });
});
