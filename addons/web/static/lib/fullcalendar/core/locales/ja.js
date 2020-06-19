(function (global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined' ? module.exports = factory() :
    typeof define === 'function' && define.amd ? define(factory) :
    (global = global || self, (global.FullCalendarLocales = global.FullCalendarLocales || {}, global.FullCalendarLocales.ja = factory()));
}(this, function () { 'use strict';

    var ja = {
        code: "ja",
        buttonText: {
            prev: "前",
            next: "次",
            today: "今日",
            month: "月",
            week: "週",
            day: "日",
            list: "予定リスト"
        },
        weekLabel: "週",
        allDayText: "終日",
        eventLimitText: function (n) {
            return "他 " + n + " 件";
        },
        noEventsMessage: "表示する予定はありません"
    };

    return ja;

}));
