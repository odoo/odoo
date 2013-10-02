$(function () {
    $(this).ajaxComplete(function(event, xhr, settings) {
        var data = JSON.parse(settings.data).params;
        if (settings.url == "/website/publish") {
            var $data = $(".oe_website_hr_recruitment .js_publish_management[data-id='" + data.id + "'][data-object='" + data.object + "']");
            if ($data.length) {
                settings.jsonpCallback = openerp.jsonRpc('/recruitment/published', 'call', data);
            }
        }
    });
});
