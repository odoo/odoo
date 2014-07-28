/**
 * Select2 Uyghur translation
 */
(function ($) {
    "use strict";
    $.fn.select2.locales['ug-CN'] = {
        formatNoMatches: function () { return "ماس كېلىدىغان ئۇچۇر تېپىلمىدى"; },
        formatInputTooShort: function (input, min) { var n = min - input.length; return "يەنە " + n + " ھەرپ كىرگۈزۈڭ";},
        formatInputTooLong: function (input, max) { var n = input.length - max; return "" + n + "ھەرپ ئۆچۈرۈڭ";},
        formatSelectionTooBig: function (limit) { return "ئەڭ كۆپ بولغاندا" + limit + " تال ئۇچۇر تاللىيالايسىز"; },
        formatLoadMore: function (pageNumber) { return "ئۇچۇرلار ئوقۇلىۋاتىدۇ…"; },
        formatSearching: function () { return "ئىزدەۋاتىدۇ…"; }
    };

    $.extend($.fn.select2.defaults, $.fn.select2.locales['ug-CN']);
})(jQuery);
