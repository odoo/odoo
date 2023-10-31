(function (global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined' ? module.exports = factory() :
    typeof define === 'function' && define.amd ? define(factory) :
    (global = global || self, (global.FullCalendarLocales = global.FullCalendarLocales || {}, global.FullCalendarLocales.nl = factory()));
}(this, function () { 'use strict';

    var nl = {
        code: "nl",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Voorgaand",
            next: "Volgende",
            today: "Vandaag",
            year: "Jaar",
            month: "Maand",
            week: "Week",
            day: "Dag",
            list: "Agenda"
        },
        allDayText: "Hele dag",
        eventLimitText: "extra",
        noEventsMessage: "Geen evenementen om te laten zien"
    };

    return nl;

}));
