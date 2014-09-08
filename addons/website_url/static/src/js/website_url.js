$(document).ready( function() {
    $("#btn_shorten_url").click( function() {
        var url = $("#url").val();
        if ($("#url").data("last_result") != url) {
            openerp.jsonRpc("/r/new", 'call', {'url' : url})
            .then(function (result) {
                $("#url").data("last_result", result).val(result).focus().select();
            });
        } else {
            alert("Please enter new URL");
            $("#url").focus().select();
        }
    });
});
