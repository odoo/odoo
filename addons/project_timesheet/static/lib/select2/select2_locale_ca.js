/**
 * Select2 Catalan translation.
 * 
 * Author: David Planella <david.planella@gmail.com>
 */
(function ($) {
    "use strict";

    $.fn.select2.locales['ca'] = {
        formatNoMatches: function () { return "No s'ha trobat cap coincidència"; },
        formatInputTooShort: function (input, min) { var n = min - input.length; return "Introduïu " + n + " caràcter" + (n == 1 ? "" : "s") + " més"; },
        formatInputTooLong: function (input, max) { var n = input.length - max; return "Introduïu " + n + " caràcter" + (n == 1? "" : "s") + "menys"; },
        formatSelectionTooBig: function (limit) { return "Només podeu seleccionar " + limit + " element" + (limit == 1 ? "" : "s"); },
        formatLoadMore: function (pageNumber) { return "S'estan carregant més resultats…"; },
        formatSearching: function () { return "S'està cercant…"; }
    };

    $.extend($.fn.select2.defaults, $.fn.select2.locales['ca']);
})(jQuery);
