(function () {
'use strict';
var website = openerp.website;

website.if_dom_contains('div.o_website_quote', function () {

    $('a.js_update_line_json').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var href = $link.attr("href");
        var order_id = href.match(/order_id=([0-9]+)/);
        var line_id = href.match(/update_line\/([0-9]+)/);
        var token = href.match(/token=(.*)/);
        openerp.jsonRpc("/quote/update_line", 'call', {
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

    var empty_sign = false;
    $('#modelaccept').on('shown.bs.modal', function (e) {
        $("#signature").empty().jSignature({'decor-color' : '#D1D0CE'});
        empty_sign = $("#signature").jSignature("getData",'image');
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
        if (token)
            token = token[1];

        var signer_name = $("#name").val();
        var sign = $("#signature").jSignature("getData",'image');
        var is_empty = sign?empty_sign[1]==sign[1]:false;
        $('#signer').toggleClass('has-error', ! signer_name);
        $('#drawsign').toggleClass('panel-danger', is_empty).toggleClass('panel-default', ! is_empty);

        if (is_empty || ! signer_name)
            return false;

        openerp.jsonRpc("/quote/accept", 'call', {
            'order_id': parseInt(order_id[1]),
            'token': token,
            'signer': signer_name,
            'sign': sign?JSON.stringify(sign[1]):false,
        }).then(function (data) {
            $('#modelaccept').modal('hide');
            window.location.href = '/quote/'+order_id[1]+'/'+token+'?message=3';
        });
        return false;
    });

    // automatically generate a menu from h1 and h2 tag in content
    var $container = $('body[data-target=".navspy"]');
    var ul = $('[data-id="quote_sidebar"]', $container);
    var sub_li = null;
    var sub_ul = null;
    $("[id^=quote_header_], [id^=quote_]", $container).attr("id", "");
    $("h1, h2", $container).each(function() {
        var id;
        switch (this.tagName.toLowerCase()) {
            case "h1":
                id = _.uniqueId('quote_header_');
                $(this.parentNode).attr('id',id);
                sub_li = $("<li>").html('<a href="#'+id+'">'+$(this).text()+'</a>').appendTo(ul);
                sub_ul = null;
                break;
            case "h2":
                id = _.uniqueId('quote_');
                if (sub_li) {
                    if (!sub_ul) {
                        sub_ul = $("<ul class='nav'>").appendTo(sub_li);
                    }
                    $(this.parentNode).attr('id',id);
                    $("<li>").html('<a href="#'+id+'">'+$(this).text()+'</a>').appendTo(sub_ul);
                }
                break;
            }
    });
});

}());
