odoo.define('website_sale.utils', function (require) {
'use strict';

function animateClone($cart, $elem, offsetTop, offsetLeft) {
    $cart.find('.o_animate_blink').addClass('o_red_highlight o_shadow_animation').delay(500).queue(function(){
        $(this).removeClass("o_shadow_animation").dequeue();
    }).delay(2000).queue(function(){
        $(this).removeClass("o_red_highlight").dequeue();
    });
    var $imgtodrag = $elem.find('img').eq(0);
    if ($imgtodrag.length) {
        var $imgclone = $imgtodrag.clone()
            .offset({
                top: $imgtodrag.offset().top,
                left: $imgtodrag.offset().left
            })
            .addClass('o_website_sale_animate')
            .appendTo(document.body)
            .animate({
                top: $cart.offset().top + offsetTop,
                left: $cart.offset().left + offsetLeft,
                width: 75,
                height: 75,
            }, 1000, 'easeInOutExpo');

        $imgclone.animate({
            width: 0,
            height: 0,
        }, function () {
            $(this).detach();
        });
    }
}

return {
    animateClone: animateClone,
};
});
