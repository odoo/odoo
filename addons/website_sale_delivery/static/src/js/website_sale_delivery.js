$(document).ready(function () {

    // $('.js_nav_month a:first').on('click', function (e) {
    //     e.preventDefault();
    //     var $ul = $(this).next("ul");
    //     if (!$ul.find('li').length) {
    //         // TODO: Why POST? (to pass the domain) A GET would be more appropriate...
    //         // This should be done server side anyway...
    //         $.post('/blog/nav', {'domain': $(this).data("domain")}, function (result) {
    //             var blog_id = +window.location.pathname.split("/").pop();
    //             $(JSON.parse(result)).each(function () {
    //                 var $li = $($.parseHTML(this.fragment));
    //                 if (blog_id == this.id) $li.addClass("active");
    //                 if (!this.website_published) $li.find('a').css("color", "red");
    //                 $ul.append($li);
    //             });

    //         });
    //     } else {
    //         $ul.toggle();
    //     }
    // });

    // When choosing an delivery carrier, update the quotation and the acquirers
    var $carrier = $("#delivery_carrier");
    $carrier.find("input[name='delivery_type']").click(function (ev) {
        var carrier_id = $(ev.currentTarget).val();
        console.log('choosing carrier', carrier_id);
        var link = $carrier.find('a');
        link.attr('href', '/shop/payment?carrier_id=' + carrier_id)
    });

});
