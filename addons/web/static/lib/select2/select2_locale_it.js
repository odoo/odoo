/**
 * Select2 Italian translation
 */
(function ($) {
    "use strict";

    $.fn.select2.locales['it'] = {
        formatNoMatches: function () { return "Nessuna corrispondenza trovata"; },
        formatInputTooShort: function (input, min) { var n = min - input.length; return "Inserisci ancora " + n + " caratter" + (n == 1? "e" : "i"); },
        formatInputTooLong: function (input, max) { var n = input.length - max; return "Inserisci " + n + " caratter" + (n == 1? "e" : "i") + " in meno"; },
        formatSelectionTooBig: function (limit) { return "Puoi selezionare solo " + limit + " element" + (limit == 1 ? "o" : "i"); },
        formatLoadMore: function (pageNumber) { return "Caricamento in corso…"; },
        formatSearching: function () { return "Ricerca…"; }
    };

    $.extend($.fn.select2.defaults, $.fn.select2.locales['it']);
})(jQuery);