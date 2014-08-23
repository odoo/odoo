// moment.js language configuration
// language : uzbek
// author : Sardor Muminov : https://github.com/muminoff

(function (factory) {
    if (typeof define === 'function' && define.amd) {
        define(['moment'], factory); // AMD
    } else if (typeof exports === 'object') {
        module.exports = factory(require('../moment')); // Node
    } else {
        factory(window.moment); // Browser global
    }
}(function (moment) {
    return moment.lang('uz', {
        months : "январь_февраль_март_апрель_май_июнь_июль_август_сентябрь_октябрь_ноябрь_декабрь".split("_"),
        monthsShort : "янв_фев_мар_апр_май_июн_июл_авг_сен_окт_ноя_дек".split("_"),
        weekdays : "Якшанба_Душанба_Сешанба_Чоршанба_Пайшанба_Жума_Шанба".split("_"),
        weekdaysShort : "Якш_Душ_Сеш_Чор_Пай_Жум_Шан".split("_"),
        weekdaysMin : "Як_Ду_Се_Чо_Па_Жу_Ша".split("_"),
        longDateFormat : {
            LT : "HH:mm",
            L : "DD/MM/YYYY",
            LL : "D MMMM YYYY",
            LLL : "D MMMM YYYY LT",
            LLLL : "D MMMM YYYY, dddd LT"
        },
        calendar : {
            sameDay : '[Бугун соат] LT [да]',
            nextDay : '[Эртага] LT [да]',
            nextWeek : 'dddd [куни соат] LT [да]',
            lastDay : '[Кеча соат] LT [да]',
            lastWeek : '[Утган] dddd [куни соат] LT [да]',
            sameElse : 'L'
        },
        relativeTime : {
            future : "Якин %s ичида",
            past : "Бир неча %s олдин",
            s : "фурсат",
            m : "бир дакика",
            mm : "%d дакика",
            h : "бир соат",
            hh : "%d соат",
            d : "бир кун",
            dd : "%d кун",
            M : "бир ой",
            MM : "%d ой",
            y : "бир йил",
            yy : "%d йил"
        },
        week : {
            dow : 1, // Monday is the first day of the week.
            doy : 7  // The week that contains Jan 4th is the first week of the year.
        }
    });
}));
