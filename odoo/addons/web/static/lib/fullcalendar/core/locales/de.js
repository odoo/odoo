(function (global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined' ? module.exports = factory() :
    typeof define === 'function' && define.amd ? define(factory) :
    (global = global || self, (global.FullCalendarLocales = global.FullCalendarLocales || {}, global.FullCalendarLocales.de = factory()));
}(this, function () { 'use strict';

    var de = {
        code: "de",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Zurück",
            next: "Vor",
            today: "Heute",
            year: "Jahr",
            month: "Monat",
            week: "Woche",
            day: "Tag",
            list: "Terminübersicht"
        },
        weekLabel: "KW",
        allDayText: "Ganztägig",
        eventLimitText: function (n) {
            return "+ weitere " + n;
        },
        noEventsMessage: "Keine Ereignisse anzuzeigen"
    };

    return de;

}));
