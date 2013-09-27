$(function () {
    $(document).on('click', '.js_publish_management .js_publish_btn', function (e) {
	var $data = $(this).parents(".js_publish_management:first");
        var loadpublish = function () {
            return openerp.jsonRpc('/recruitment/published', 'call', {'id': $data.data('id')});
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
