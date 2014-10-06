/**
 * Select2 Traditional Chinese translation
 */
(function ($) {
    "use strict";
    $.fn.select2.locales['zh-TW'] = {
        formatNoMatches: function () { return "沒有找到相符的項目"; },
        formatInputTooShort: function (input, min) { var n = min - input.length; return "請再輸入" + n + "個字元";},
        formatInputTooLong: function (input, max) { var n = input.length - max; return "請刪掉" + n + "個字元";},
        formatSelectionTooBig: function (limit) { return "你只能選擇最多" + limit + "項"; },
        formatLoadMore: function (pageNumber) { return "載入中…"; },
        formatSearching: function () { return "搜尋中…"; }
    };

    $.extend($.fn.select2.defaults, $.fn.select2.locales['zh-TW']);
})(jQuery);
