/**
 * Select2 Icelandic translation.
 */
(function ($) {
    "use strict";

    $.fn.select2.locales['is'] = {
        formatNoMatches: function () { return "Ekkert fannst"; },
        formatInputTooShort: function (input, min) { var n = min - input.length; return "Vinsamlegast skrifið " + n + " staf" + (n > 1 ? "i" : "") + " í viðbót"; },
        formatInputTooLong: function (input, max) { var n = input.length - max; return "Vinsamlegast styttið texta um " + n + " staf" + (n > 1 ? "i" : ""); },
        formatSelectionTooBig: function (limit) { return "Þú getur aðeins valið " + limit + " atriði"; },
        formatLoadMore: function (pageNumber) { return "Sæki fleiri niðurstöður…"; },
        formatSearching: function () { return "Leita…"; }
    };

    $.extend($.fn.select2.defaults, $.fn.select2.locales['is']);
})(jQuery);
