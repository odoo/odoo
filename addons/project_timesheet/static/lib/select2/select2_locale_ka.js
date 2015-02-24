/**
 * Select2 Georgian (Kartuli) translation.
 * 
 * Author: Dimitri Kurashvili dimakura@gmail.com
 */
(function ($) {
    "use strict";

    $.fn.select2.locales['ka'] = {
        formatNoMatches: function () { return "ვერ მოიძებნა"; },
        formatInputTooShort: function (input, min) { var n = min - input.length; return "გთხოვთ შეიყვანოთ კიდევ " + n + " სიმბოლო"; },
        formatInputTooLong: function (input, max) { var n = input.length - max; return "გთხოვთ წაშალოთ " + n + " სიმბოლო"; },
        formatSelectionTooBig: function (limit) { return "თქვენ შეგიძლიათ მხოლოდ " + limit + " ჩანაწერის მონიშვნა"; },
        formatLoadMore: function (pageNumber) { return "შედეგის ჩატვირთვა…"; },
        formatSearching: function () { return "ძებნა…"; }
    };

    $.extend($.fn.select2.defaults, $.fn.select2.locales['ka']);
})(jQuery);
