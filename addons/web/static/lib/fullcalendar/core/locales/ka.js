(function (global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined' ? module.exports = factory() :
    typeof define === 'function' && define.amd ? define(factory) :
    (global = global || self, (global.FullCalendarLocales = global.FullCalendarLocales || {}, global.FullCalendarLocales.ka = factory()));
}(this, function () { 'use strict';

    var ka = {
        code: "ka",
        week: {
            dow: 1,
            doy: 7
        },
        buttonText: {
            prev: "წინა",
            next: "შემდეგი",
            today: "დღეს",
            month: "თვე",
            week: "კვირა",
            day: "დღე",
            list: "დღის წესრიგი"
        },
        weekLabel: "კვ",
        allDayText: "მთელი დღე",
        eventLimitText: function (n) {
            return "+ კიდევ " + n;
        },
        noEventsMessage: "ღონისძიებები არ არის"
    };

    return ka;

}));
