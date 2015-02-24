/**
 * Select2 Serbian translation.
 *
 * @author  Limon Monte <limon.monte@gmail.com>
 */
(function ($) {
    "use strict";

    $.fn.select2.locales['rs'] = {
        formatNoMatches: function () { return "Ništa nije pronađeno"; },
        formatInputTooShort: function (input, min) { var n = min - input.length; return "Ukucajte bar još " + n + " simbol" + (n % 10 == 1 && n % 100 != 11 ? "" : "a"); },
        formatInputTooLong: function (input, max) { var n = input.length - max; return "Obrišite " + n + " simbol" + (n % 10 == 1 && n % 100 != 11	 ? "" : "a"); },
        formatSelectionTooBig: function (limit) { return "Možete izabrati samo " + limit + " stavk" + (limit % 10 == 1 && limit % 100 != 11	 ? "u" : (limit % 10 >= 2 && limit % 10 <= 4 && (limit % 100 < 12 || limit % 100 > 14)? "e" : "i")); },
        formatLoadMore: function (pageNumber) { return "Preuzimanje još rezultata…"; },
        formatSearching: function () { return "Pretraga…"; }
    };

    $.extend($.fn.select2.defaults, $.fn.select2.locales['rs']);
})(jQuery);
