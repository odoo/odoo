/**
 * Select2 Vietnamese translation.
 * 
 * Author: Long Nguyen <olragon@gmail.com>
 */
(function ($) {
    "use strict";

    $.fn.select2.locales['vi'] = {
        formatNoMatches: function () { return "Không tìm thấy kết quả"; },
        formatInputTooShort: function (input, min) { var n = min - input.length; return "Vui lòng nhập nhiều hơn " + n + " ký tự" + (n == 1 ? "" : "s"); },
        formatInputTooLong: function (input, max) { var n = input.length - max; return "Vui lòng nhập ít hơn " + n + " ký tự" + (n == 1? "" : "s"); },
        formatSelectionTooBig: function (limit) { return "Chỉ có thể chọn được " + limit + " tùy chọn" + (limit == 1 ? "" : "s"); },
        formatLoadMore: function (pageNumber) { return "Đang lấy thêm kết quả…"; },
        formatSearching: function () { return "Đang tìm…"; }
    };

    $.extend($.fn.select2.defaults, $.fn.select2.locales['vi']);
})(jQuery);

