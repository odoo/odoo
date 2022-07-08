odoo.define('website_sale.utils', function (require) {
'use strict';

/**
 * Gets the element in the navbar currently displayed.
 * Depending on the scroll position, it could either be the one in the main
 * top bar or the one in the affixed navbar.
 *
 * @private
 * @param {string} selector
 * @returns {jQuery}
 */
function getNavBarButton(selector) {
    var $affixedHeaderButton = $('header.affixed ' + selector);
    if ($affixedHeaderButton.length) {
        return $affixedHeaderButton;
    } else {
        return $('header ' + selector).first();
    }
}

function animateClone($cart, $elem, offsetTop, offsetLeft) {
    $cart.find('.o_animate_blink').addClass('o_red_highlight o_shadow_animation').delay(500).queue(function () {
        $(this).removeClass("o_shadow_animation").dequeue();
    }).delay(2000).queue(function () {
        $(this).removeClass("o_red_highlight").dequeue();
    });
    return new Promise(function (resolve, reject) {
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
                resolve();
                $(this).detach();
            });
        } else {
            resolve();
        }
    });
}

/**
 * Updates both navbar cart
 * @param {Object} data
 */
function updateCartNavBar(data) {
    $(".my_cart_quantity")
        .parents('li.o_wsale_my_cart').removeClass('d-none').end()
        .toggleClass('fa fa-warning', !data.cart_quantity)
        .attr('title', data.warning)
        .text(data.cart_quantity || '')
        .hide()
        .fadeIn(600);

    $(".js_cart_lines").first().before(data['website_sale.cart_lines']).end().remove();
    $(".js_cart_summary").first().before(data['website_sale.short_cart_summary']).end().remove();
}

/**
 * Displays `message` in an alert box at the top of the page if it's a
 * non-empty string.
 *
 * @param {string | null} message
 */
function showWarning(message) {
    if (!message) {
        return;
    }
    var $page = $('.oe_website_sale');
    var cart_alert = $page.children('#data_warning');
    if (!cart_alert.length) {
        cart_alert = $(
            '<div class="alert alert-danger alert-dismissible" role="alert" id="data_warning">' +
                '<button type="button" class="close" data-dismiss="alert">&times;</button> ' +
                '<span></span>' +
            '</div>').prependTo($page);
    }
    cart_alert.children('span:last-child').text(message);
}

return {
    animateClone: animateClone,
    getNavBarButton: getNavBarButton,
    updateCartNavBar: updateCartNavBar,
    showWarning: showWarning,
};
});
