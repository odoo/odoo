/** @odoo-module **/

import { intersperse } from "@web/core/utils/strings";
import { localization } from "@web/core/l10n/localization";

/**
 * Inserts "thousands" separators in the provided number.
 *
 * @private
 * @param {string} string representing integer number
 * @returns {string}
 */
export function insertThousandsSep(number) {
    const { thousandsSep, grouping } = localization;
    const negative = number[0] === "-";
    number = negative ? number.slice(1) : number;
    return (negative ? "-" : "") + intersperse(number, grouping, thousandsSep);
}

/**
 * Returns the price formatted according to the selected l10n.
 *
 * @param {float} price
 */
export function priceToStr(price) {
    let precision = 2;
    const decimalPrecisionEl = document.querySelector(".decimal_precision");
    if (decimalPrecisionEl) {
        precision = parseInt(decimalPrecisionEl.dataset.precision);
    }
    const formatted = _.str.sprintf(`%.${precision}f`, price).split(".");
    formatted[0] = insertThousandsSep(formatted[0]);
    return formatted.join(localization.decimalPoint);
}

/**
 * Updates both navbar cart
 *
 * @param {Object} data
 */
export function updateCartNavBar(data) {
    $(".my_cart_quantity")
        .parents("li.o_wsale_my_cart")
        .removeClass("d-none")
        .end()
        .addClass("o_mycart_zoom_animation")
        .delay(300)
        .queue(function () {
            $(this)
                .toggleClass("fa fa-warning", !data.cart_quantity)
                .attr("title", data.warning)
                .text(data.cart_quantity || "")
                .removeClass("o_mycart_zoom_animation")
                .dequeue();
        });

    $(".js_cart_lines").first().before(data["website_sale.cart_lines"]).end().remove();
    $(".js_cart_summary").replaceWith(data["website_sale.short_cart_summary"]);
}

export function animateClone($cart, $elem, offsetTop, offsetLeft) {
    if (!$cart.length) {
        return Promise.resolve();
    }
    $cart.find('.o_animate_blink').addClass('o_red_highlight o_shadow_animation').delay(500).queue(function () {
        $(this).removeClass("o_shadow_animation").dequeue();
    }).delay(2000).queue(function () {
        $(this).removeClass("o_red_highlight").dequeue();
    });
    return new Promise(function (resolve, reject) {
        if(!$elem) resolve();
        var $imgtodrag = $elem.find('img').eq(0);
        if ($imgtodrag.length) {
            var $imgclone = $imgtodrag.clone()
                .offset({
                    top: $imgtodrag.offset().top,
                    left: $imgtodrag.offset().left
                })
                .removeClass()
                .addClass('o_website_sale_animate')
                .appendTo(document.body)
                .css({
                    // Keep the same size on cloned img.
                    width: $imgtodrag.width(),
                    height: $imgtodrag.height(),
                })
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
