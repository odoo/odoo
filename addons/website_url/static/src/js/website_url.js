$(document).ready( function() {
    ZeroClipboard.config(
        {swfPath: location.origin + "/website_url/static/src/js/ZeroClipboard.swf" }
    );
    var client = new ZeroClipboard($("#btn_shorten_url"));
    $("#btn_shorten_url").click( function() {
        if($(this).attr('class').indexOf('btn_copy') === -1) {
            var url = $("#url").val();
            openerp.jsonRpc("/r/new", 'call', {'url' : url})
                .then(function (result) {
                    $("#url").data("last_result", result).val(result).focus().select();
                    $("#btn_shorten_url").text("Copy").removeClass("btn_shorten btn-primary").addClass("btn_copy btn-success");
                });
        }
    });
    $("#url").on("change keyup paste mouseup", function() {
        if ($(this).data("last_result") != $("#url").val()) {
            $("#btn_shorten_url").text("Shorten").removeClass("btn_copy btn-success").addClass("btn_shorten btn-primary");
        }
    });
});
