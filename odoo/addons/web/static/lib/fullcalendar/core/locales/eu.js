(function (global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined' ? module.exports = factory() :
    typeof define === 'function' && define.amd ? define(factory) :
    (global = global || self, (global.FullCalendarLocales = global.FullCalendarLocales || {}, global.FullCalendarLocales.eu = factory()));
}(this, function () { 'use strict';

    var eu = {
        code: "eu",
        week: {
            dow: 1,
            doy: 7 // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: "Aur",
            next: "Hur",
            today: "Gaur",
            month: "Hilabetea",
            week: "Astea",
            day: "Eguna",
            list: "Agenda"
        },
        weekLabel: "As",
        allDayHtml: "Egun<br/>osoa",
        eventLimitText: "gehiago",
        noEventsMessage: "Ez dago ekitaldirik erakusteko"
    };

    return eu;

}));
