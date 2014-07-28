/**
 * Select2 Korean translation.
 * 
 * @author  Swen Mun <longfinfunnel@gmail.com>
 */
(function ($) {
    "use strict";

    $.fn.select2.locales['ko'] = {
        formatNoMatches: function () { return "결과 없음"; },
        formatInputTooShort: function (input, min) { var n = min - input.length; return "너무 짧습니다. "+n+"글자 더 입력해주세요."; },
        formatInputTooLong: function (input, max) { var n = input.length - max; return "너무 깁니다. "+n+"글자 지워주세요."; },
        formatSelectionTooBig: function (limit) { return "최대 "+limit+"개까지만 선택하실 수 있습니다."; },
        formatLoadMore: function (pageNumber) { return "불러오는 중…"; },
        formatSearching: function () { return "검색 중…"; }
    };

    $.extend($.fn.select2.defaults, $.fn.select2.locales['ko']);
})(jQuery);
