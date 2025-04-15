(function (global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined' ? module.exports = factory() :
    typeof define === 'function' && define.amd ? define(factory) :
    (global = global || self, (global.FullCalendarLocales = global.FullCalendarLocales || {}, global.FullCalendarLocales.bs = factory()));
}(this, function () { 'use strict';

    var bs = {
        code: "bs",
        week: {
            dow: 1,
            doy: 7 // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: "Prošli",
            next: "Sljedeći",
            today: "Danas",
            month: "Mjesec",
            week: "Sedmica",
            day: "Dan",
            list: "Raspored"
        },
        weekLabel: "Sed",
        allDayText: "Cijeli dan",
        eventLimitText: function (n) {
            return "+ još " + n;
        },
        noEventsMessage: "Nema događaja za prikazivanje"
    };

    return bs;

}));
