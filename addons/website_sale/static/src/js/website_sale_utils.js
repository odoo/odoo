odoo.define('website_sale.utils', function (require) {
    "use strict";

    var animate_clone =  function(cart, $elem, offset_top, offset_left) {
        cart.find('.o_animate_blink').addClass('o_red_highlight o_shadow_animation').delay(500).queue(function(){
            $(this).removeClass("o_shadow_animation").dequeue();
        });
        var imgtodrag = $elem.find('img').eq(0);
        if (imgtodrag.length) {
            var imgclone = imgtodrag.clone()
            .offset({
                top: imgtodrag.offset().top,
                left: imgtodrag.offset().left
            })
            .addClass('o_website_sale_animate')
            .appendTo($('body'))
            .animate({
                'top': cart.offset().top + offset_top,
                'left': cart.offset().left + offset_left,
                'width': 75,
                'height': 75
            }, 1000, 'easeInOutExpo');

            imgclone.animate({
                'width': 0,
                'height': 0
            }, function () {
                $(this).detach();
            });
        }
    };

    return {
        animate_clone: animate_clone,
    };

});
