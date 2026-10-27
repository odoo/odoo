(function (global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined' ? module.exports = factory() :
    typeof define === 'function' && define.amd ? define(factory) :
    (global = global || self, (global.FullCalendarLocales = global.FullCalendarLocales || {}, global.FullCalendarLocales['ar-kw'] = factory()));
}(this, function () { 'use strict';

    var arKw = {
        code: "ar-kw",
        week: {
            dow: 0,
            doy: 12 // The week that contains Jan 1st is the first week of the year.
        },
        dir: 'rtl',
        buttonText: {
            prev: "السابق",
            next: "التالي",
            today: "اليوم",
            month: "شهر",
            week: "أسبوع",
            day: "يوم",
            list: "أجندة"
        },
        weekLabel: "أسبوع",
        allDayText: "اليوم كله",
        eventLimitText: "أخرى",
        noEventsMessage: "أي أحداث لعرض"
    };

    return arKw;

}));
