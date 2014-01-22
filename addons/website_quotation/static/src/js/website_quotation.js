$(document).ready(function () {
    $('a.js_update_line_json').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var href = $link.attr("href");
        var order_id = href.match(/order_id=([0-9]+)/);
        var line_id = href.match(/update_line\/([0-9]+)/);
        var token = href.match(/token=(.*)/);
        openerp.jsonRpc("/quote/update_line/", 'call', {
                'line_id': line_id[1],
                'order_id': parseInt(order_id[1]),
                'token': token[1],
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

    $('#modelaccept').on('shown.bs.modal', function (e) {
        $("#signature").empty().jSignature();
    });

    $('#sign_clean').on('click', function (e) {
        $("#signature").jSignature('reset');
    });

    $('form.js_accept_json').submit(function(ev){
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var href = $link.attr("action");
        var order_id = href.match(/accept\/([0-9]+)/);
        var token = href.match(/token=(.*)/);
        var sign = false;
        var signer_name = false;
        if($('#signature').length > 0){
            var isSignature=$("#signature").jSignature('getData','base30')[1].length>1?true:false;
            if (isSignature)
                sign = JSON.stringify($("#signature").jSignature("getData",'image')[1]);
            signer_name = $("#name").val();
        }
        openerp.jsonRpc("/quote/accept/", 'call', {
            'order_id': parseInt(order_id[1]),
            'token': token[1],
            'signer': signer_name,
            'sign': sign,
        })
        .then(function (data) {
            if(!_.isEmpty(data)){
                $('#modelaccept').modal('hide');
                var url = location.protocol+'//'+location.hostname+(location.port ? ':'+location.port : "")
                window.location.replace(url +'/quote/'+order_id[1]+'/'+token[1]+'?message=3');
            } else{
                if (data[0]['signer']) $('#signer').addClass('has-error'); else $('#signer').removeClass('has-error');
                if (data[0]['sign']) $('#drawsign').addClass('panel-danger'); else $('#drawsign').removeClass('panel-danger');
            }
        });
        return false
    });
    // automatically generate a menu from h1 and h1 tag in content
    var ul = $('[data-id="quote_sidebar"]');
    var sub_li = null;
    var sub_ul = null;
    ul.empty();
    $("section h1, section h2").each(function() {
        switch (this.tagName.toLowerCase()) {
            case "h1":
                id = _.uniqueId('quote_header_')
                $(this.parentNode).attr('id',id)
                sub_li = $("<li>").html('<a href="#'+id+'">'+$(this).text()+'</a>').appendTo(ul);
                sub_ul = null;
                break;
            case "h2":
                id = _.uniqueId('quote_')
                if (sub_li) {
                    if (!sub_ul) {
                        sub_ul = $("<ul class='nav'>").appendTo(sub_li);
                    }
                    $(this.parentNode).attr('id',id)
                    $("<li>").html('<a href="#'+id+'">'+$(this).text()+'</a>').appendTo(sub_ul);
                }
                break;
            }
    });

var target_date = new Date($('#validity_date').val());

setInterval(function () {
    var current_date = new Date();
    var days_left = Math.floor((target_date - current_date)/86400000);
    $('#countdown').html('<span><i class="fa fa-clock-o fa-2x"/><span class="day_counter">'+((days_left > 0) ? days_left : 0)+'</span><small class="days_left">Days</small></span>')
}, 1000);

//vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
});
