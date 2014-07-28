/**
 * Select2 Galician translation
 * 
 * Author: Leandro Regueiro <leandro.regueiro@gmail.com>
 */
(function ($) {
    "use strict";

    $.fn.select2.locales['gl'] = {
        formatNoMatches: function () {
            return "Non se atoparon resultados";
        },
        formatInputTooShort: function (input, min) {
            var n = min - input.length;
            if (n === 1) {
                return "Engada un carácter";
            } else {
                return "Engada " + n + " caracteres";
            }
        },
        formatInputTooLong: function (input, max) {
            var n = input.length - max;
            if (n === 1) {
                return "Elimine un carácter";
            } else {
                return "Elimine " + n + " caracteres";
            }
        },
        formatSelectionTooBig: function (limit) {
            if (limit === 1 ) {
                return "Só pode seleccionar un elemento";
            } else {
                return "Só pode seleccionar " + limit + " elementos";
            }
        },
        formatLoadMore: function (pageNumber) {
            return "Cargando máis resultados…";
        },
        formatSearching: function () {
            return "Buscando…";
        }
    };

    $.extend($.fn.select2.defaults, $.fn.select2.locales['gl']);
})(jQuery);
