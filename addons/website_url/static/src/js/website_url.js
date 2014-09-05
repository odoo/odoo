$(document).ready( function() {
    $("#btn_shorten_url").click( function() {
        openerp.jsonRpc("/r/new", 'call', {'url' : $("#url").val()})
            .then(function (result) {
                if (result == false) {
                    //Impliment functionality of coping shorten url to clipboard
                    // create alert-error of bootstrap which is above the url
                    /*<div class="alert alert-warning alert-dismissible" role="alert">
  <button type="button" class="close" data-dismiss="alert"><span aria-hidden="true">&times;</span><span class="sr-only">Close</span></button>
  <strong>Warning!</strong> Better check yourself, you're not looking too good.
</div>*/
                } else {
                    $("#btn_shorten_url").text("Copy");
                    $("#url").val(result).focus().select();
                }
            });
    });
});
