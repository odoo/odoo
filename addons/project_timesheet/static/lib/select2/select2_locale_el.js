/**
 * Select2 Greek translation.
 * 
 * @author  Uriy Efremochkin <efremochkin@uriy.me>
 */
(function ($) {
    "use strict";

    $.fn.select2.locales['el'] = {
        formatNoMatches: function () { return "Δεν βρέθηκαν αποτελέσματα"; },
        formatInputTooShort: function (input, min) { var n = min - input.length; return "Παρακαλούμε εισάγετε " + n + " περισσότερο" + (n > 1 ? "υς" : "") + " χαρακτήρ" + (n > 1 ? "ες" : "α"); },
        formatInputTooLong: function (input, max) { var n = input.length - max; return "Παρακαλούμε διαγράψτε " + n + " χαρακτήρ" + (n > 1 ? "ες" : "α"); },
        formatSelectionTooBig: function (limit) { return "Μπορείτε να επιλέξετε μόνο " + limit + " αντικείμεν" + (limit > 1 ? "α" : "ο"); },
        formatLoadMore: function (pageNumber) { return "Φόρτωση περισσότερων…"; },
        formatSearching: function () { return "Αναζήτηση…"; }
    };

    $.extend($.fn.select2.defaults, $.fn.select2.locales['el']);
})(jQuery);