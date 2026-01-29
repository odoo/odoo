(function (global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined' ? module.exports = factory() :
    typeof define === 'function' && define.amd ? define(factory) :
    (global = global || self, (global.FullCalendarLocales = global.FullCalendarLocales || {}, global.FullCalendarLocales.ro = factory()));
}(this, function () { 'use strict';

    var ro = {
        code: "ro",
        week: {
            dow: 1,
            doy: 7 // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: "precedentă",
            next: "următoare",
            today: "Azi",
            month: "Lună",
            week: "Săptămână",
            day: "Zi",
            list: "Agendă"
        },
        weekLabel: "Săpt",
        allDayText: "Toată ziua",
        eventLimitText: function (n) {
            return "+alte " + n;
        },
        noEventsMessage: "Nu există evenimente de afișat"
    };

    return ro;

}));
