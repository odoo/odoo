/**
 * Select2 Latvian translation.
 *
 * @author  Uriy Efremochkin <efremochkin@uriy.me>
 */
(function ($) {
    "use strict";

    $.fn.select2.locales['lv'] = {
        formatNoMatches: function () { return "Sakritību nav"; },
        formatInputTooShort: function (input, min) { var n = min - input.length; return "Lūdzu ievadiet vēl " + n + " simbol" + (n == 11 ? "us" : n%10 == 1 ? "u" : "us"); },
        formatInputTooLong: function (input, max) { var n = input.length - max; return "Lūdzu ievadiet par " + n + " simbol" + (n == 11 ? "iem" : n%10 == 1 ? "u" : "iem") + " mazāk"; },
        formatSelectionTooBig: function (limit) { return "Jūs varat izvēlēties ne vairāk kā " + limit + " element" + (limit == 11 ? "us" : limit%10 == 1 ? "u" : "us"); },
        formatLoadMore: function (pageNumber) { return "Datu ielāde…"; },
        formatSearching: function () { return "Meklēšana…"; }
    };

    $.extend($.fn.select2.defaults, $.fn.select2.locales['lv']);
})(jQuery);
