/*!
FullCalendar Core v6.1.20
Docs & License: https://fullcalendar.io
(c) 2024 Adam Shaw
*/
(function (index_js) {
    'use strict';

    var l0 = {
        code: 'af',
        week: {
            dow: 1,
            doy: 4, // Die week wat die 4de Januarie bevat is die eerste week van die jaar.
        },
        buttonText: {
            prev: 'Vorige',
            next: 'Volgende',
            today: 'Vandag',
            year: 'Jaar',
            month: 'Maand',
            week: 'Week',
            day: 'Dag',
            list: 'Agenda',
        },
        allDayText: 'Heeldag',
        moreLinkText: 'Addisionele',
        noEventsText: 'Daar is geen gebeurtenisse nie',
    };

    var l1 = {
        code: 'ar-dz',
        week: {
            dow: 0,
            doy: 4, // The week that contains Jan 1st is the first week of the year.
        },
        direction: 'rtl',
        buttonText: {
            prev: 'السابق',
            next: 'التالي',
            today: 'اليوم',
            year: 'سنة',
            month: 'شهر',
            week: 'أسبوع',
            day: 'يوم',
            list: 'أجندة',
        },
        weekText: 'أسبوع',
        allDayText: 'اليوم كله',
        moreLinkText: 'أخرى',
        noEventsText: 'أي أحداث لعرض',
    };

    var l2 = {
        code: 'ar-kw',
        week: {
            dow: 0,
            doy: 12, // The week that contains Jan 1st is the first week of the year.
        },
        direction: 'rtl',
        buttonText: {
            prev: 'السابق',
            next: 'التالي',
            today: 'اليوم',
            year: 'سنة',
            month: 'شهر',
            week: 'أسبوع',
            day: 'يوم',
            list: 'أجندة',
        },
        weekText: 'أسبوع',
        allDayText: 'اليوم كله',
        moreLinkText: 'أخرى',
        noEventsText: 'أي أحداث لعرض',
    };

    var l3 = {
        code: 'ar-ly',
        week: {
            dow: 6,
            doy: 12, // The week that contains Jan 1st is the first week of the year.
        },
        direction: 'rtl',
        buttonText: {
            prev: 'السابق',
            next: 'التالي',
            today: 'اليوم',
            year: 'سنة',
            month: 'شهر',
            week: 'أسبوع',
            day: 'يوم',
            list: 'أجندة',
        },
        weekText: 'أسبوع',
        allDayText: 'اليوم كله',
        moreLinkText: 'أخرى',
        noEventsText: 'أي أحداث لعرض',
    };

    var l4 = {
        code: 'ar-ma',
        week: {
            dow: 6,
            doy: 12, // The week that contains Jan 1st is the first week of the year.
        },
        direction: 'rtl',
        buttonText: {
            prev: 'السابق',
            next: 'التالي',
            today: 'اليوم',
            year: 'سنة',
            month: 'شهر',
            week: 'أسبوع',
            day: 'يوم',
            list: 'أجندة',
        },
        weekText: 'أسبوع',
        allDayText: 'اليوم كله',
        moreLinkText: 'أخرى',
        noEventsText: 'أي أحداث لعرض',
    };

    var l5 = {
        code: 'ar-sa',
        week: {
            dow: 0,
            doy: 6, // The week that contains Jan 1st is the first week of the year.
        },
        direction: 'rtl',
        buttonText: {
            prev: 'السابق',
            next: 'التالي',
            today: 'اليوم',
            year: 'سنة',
            month: 'شهر',
            week: 'أسبوع',
            day: 'يوم',
            list: 'أجندة',
        },
        weekText: 'أسبوع',
        allDayText: 'اليوم كله',
        moreLinkText: 'أخرى',
        noEventsText: 'أي أحداث لعرض',
    };

    var l6 = {
        code: 'ar-tn',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        direction: 'rtl',
        buttonText: {
            prev: 'السابق',
            next: 'التالي',
            today: 'اليوم',
            year: 'سنة',
            month: 'شهر',
            week: 'أسبوع',
            day: 'يوم',
            list: 'أجندة',
        },
        weekText: 'أسبوع',
        allDayText: 'اليوم كله',
        moreLinkText: 'أخرى',
        noEventsText: 'أي أحداث لعرض',
    };

    var l7 = {
        code: 'ar',
        week: {
            dow: 6,
            doy: 12, // The week that contains Jan 1st is the first week of the year.
        },
        direction: 'rtl',
        buttonText: {
            prev: 'السابق',
            next: 'التالي',
            today: 'اليوم',
            year: 'سنة',
            month: 'شهر',
            week: 'أسبوع',
            day: 'يوم',
            list: 'أجندة',
        },
        weekText: 'أسبوع',
        allDayText: 'اليوم كله',
        moreLinkText: 'أخرى',
        noEventsText: 'أي أحداث لعرض',
    };

    var l8 = {
        code: 'az',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Əvvəl',
            next: 'Sonra',
            today: 'Bu Gün',
            year: 'Il',
            month: 'Ay',
            week: 'Həftə',
            day: 'Gün',
            list: 'Gündəm',
        },
        weekText: 'Həftə',
        allDayText: 'Bütün Gün',
        moreLinkText(n) {
            return '+ daha çox ' + n;
        },
        noEventsText: 'Göstərmək üçün hadisə yoxdur',
    };

    var l9 = {
        code: 'bg',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'назад',
            next: 'напред',
            today: 'днес',
            year: 'година',
            month: 'Месец',
            week: 'Седмица',
            day: 'Ден',
            list: 'График',
        },
        allDayText: 'Цял ден',
        moreLinkText(n) {
            return '+още ' + n;
        },
        noEventsText: 'Няма събития за показване',
    };

    var l10 = {
        code: 'bn',
        week: {
            dow: 0,
            doy: 6, // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: 'পেছনে',
            next: 'সামনে',
            today: 'আজ',
            year: 'বছর',
            month: 'মাস',
            week: 'সপ্তাহ',
            day: 'দিন',
            list: 'তালিকা',
        },
        weekText: 'সপ্তাহ',
        allDayText: 'সারাদিন',
        moreLinkText(n) {
            return '+অন্যান্য ' + n;
        },
        noEventsText: 'কোনো ইভেন্ট নেই',
    };

    var l11 = {
        code: 'bs',
        week: {
            dow: 1,
            doy: 7, // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: 'Prošli',
            next: 'Sljedeći',
            today: 'Danas',
            year: 'Godina',
            month: 'Mjesec',
            week: 'Sedmica',
            day: 'Dan',
            list: 'Raspored',
        },
        weekText: 'Sed',
        allDayText: 'Cijeli dan',
        moreLinkText(n) {
            return '+ još ' + n;
        },
        noEventsText: 'Nema događaja za prikazivanje',
    };

    var l12 = {
        code: 'ca',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Anterior',
            next: 'Següent',
            today: 'Avui',
            year: 'Any',
            month: 'Mes',
            week: 'Setmana',
            day: 'Dia',
            list: 'Agenda',
        },
        weekText: 'Set',
        allDayText: 'Tot el dia',
        moreLinkText: 'més',
        noEventsText: 'No hi ha esdeveniments per mostrar',
    };

    var l13 = {
        code: 'cs',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Dříve',
            next: 'Později',
            today: 'Nyní',
            year: 'Rok',
            month: 'Měsíc',
            week: 'Týden',
            day: 'Den',
            list: 'Agenda',
        },
        weekText: 'Týd',
        allDayText: 'Celý den',
        moreLinkText(n) {
            return '+další: ' + n;
        },
        noEventsText: 'Žádné akce k zobrazení',
    };

    var l14 = {
        code: 'cy',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Blaenorol',
            next: 'Nesaf',
            today: 'Heddiw',
            year: 'Blwyddyn',
            month: 'Mis',
            week: 'Wythnos',
            day: 'Dydd',
            list: 'Rhestr',
        },
        weekText: 'Wythnos',
        allDayText: 'Trwy\'r dydd',
        moreLinkText: 'Mwy',
        noEventsText: 'Dim digwyddiadau',
    };

    var l15 = {
        code: 'da',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Forrige',
            next: 'Næste',
            today: 'I dag',
            year: 'År',
            month: 'Måned',
            week: 'Uge',
            day: 'Dag',
            list: 'Agenda',
        },
        weekText: 'Uge',
        allDayText: 'Hele dagen',
        moreLinkText: 'flere',
        noEventsText: 'Ingen arrangementer at vise',
    };

    function affix$1(buttonText) {
        return (buttonText === 'Tag' || buttonText === 'Monat') ? 'r' :
            buttonText === 'Jahr' ? 's' : '';
    }
    var l16 = {
        code: 'de-at',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Zurück',
            next: 'Vor',
            today: 'Heute',
            year: 'Jahr',
            month: 'Monat',
            week: 'Woche',
            day: 'Tag',
            list: 'Terminübersicht',
        },
        weekText: 'KW',
        weekTextLong: 'Woche',
        allDayText: 'Ganztägig',
        moreLinkText(n) {
            return '+ weitere ' + n;
        },
        noEventsText: 'Keine Ereignisse anzuzeigen',
        buttonHints: {
            prev(buttonText) {
                return `Vorherige${affix$1(buttonText)} ${buttonText}`;
            },
            next(buttonText) {
                return `Nächste${affix$1(buttonText)} ${buttonText}`;
            },
            today(buttonText) {
                // → Heute, Diese Woche, Dieser Monat, Dieses Jahr
                if (buttonText === 'Tag') {
                    return 'Heute';
                }
                return `Diese${affix$1(buttonText)} ${buttonText}`;
            },
        },
        viewHint(buttonText) {
            // → Tagesansicht, Wochenansicht, Monatsansicht, Jahresansicht
            const glue = buttonText === 'Woche' ? 'n' : buttonText === 'Monat' ? 's' : 'es';
            return buttonText + glue + 'ansicht';
        },
        navLinkHint: 'Gehe zu $0',
        moreLinkHint(eventCnt) {
            return 'Zeige ' + (eventCnt === 1 ?
                'ein weiteres Ereignis' :
                eventCnt + ' weitere Ereignisse');
        },
        closeHint: 'Schließen',
        timeHint: 'Uhrzeit',
        eventHint: 'Ereignis',
    };

    function affix(buttonText) {
        return (buttonText === 'Tag' || buttonText === 'Monat') ? 'r' :
            buttonText === 'Jahr' ? 's' : '';
    }
    var l17 = {
        code: 'de',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Zurück',
            next: 'Vor',
            today: 'Heute',
            year: 'Jahr',
            month: 'Monat',
            week: 'Woche',
            day: 'Tag',
            list: 'Terminübersicht',
        },
        weekText: 'KW',
        weekTextLong: 'Woche',
        allDayText: 'Ganztägig',
        moreLinkText(n) {
            return '+ weitere ' + n;
        },
        noEventsText: 'Keine Ereignisse anzuzeigen',
        buttonHints: {
            prev(buttonText) {
                return `Vorherige${affix(buttonText)} ${buttonText}`;
            },
            next(buttonText) {
                return `Nächste${affix(buttonText)} ${buttonText}`;
            },
            today(buttonText) {
                // → Heute, Diese Woche, Dieser Monat, Dieses Jahr
                if (buttonText === 'Tag') {
                    return 'Heute';
                }
                return `Diese${affix(buttonText)} ${buttonText}`;
            },
        },
        viewHint(buttonText) {
            // → Tagesansicht, Wochenansicht, Monatsansicht, Jahresansicht
            const glue = buttonText === 'Woche' ? 'n' : buttonText === 'Monat' ? 's' : 'es';
            return buttonText + glue + 'ansicht';
        },
        navLinkHint: 'Gehe zu $0',
        moreLinkHint(eventCnt) {
            return 'Zeige ' + (eventCnt === 1 ?
                'ein weiteres Ereignis' :
                eventCnt + ' weitere Ereignisse');
        },
        closeHint: 'Schließen',
        timeHint: 'Uhrzeit',
        eventHint: 'Ereignis',
    };

    var l18 = {
        code: 'el',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4st is the first week of the year.
        },
        buttonText: {
            prev: 'Προηγούμενος',
            next: 'Επόμενος',
            today: 'Σήμερα',
            year: 'Ετος',
            month: 'Μήνας',
            week: 'Εβδομάδα',
            day: 'Ημέρα',
            list: 'Ατζέντα',
        },
        weekText: 'Εβδ',
        allDayText: 'Ολοήμερο',
        moreLinkText: 'περισσότερα',
        noEventsText: 'Δεν υπάρχουν γεγονότα προς εμφάνιση',
    };

    var l19 = {
        code: 'en-au',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonHints: {
            prev: 'Previous $0',
            next: 'Next $0',
            today: 'This $0',
        },
        viewHint: '$0 view',
        navLinkHint: 'Go to $0',
        moreLinkHint(eventCnt) {
            return `Show ${eventCnt} more event${eventCnt === 1 ? '' : 's'}`;
        },
    };

    var l20 = {
        code: 'en-gb',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonHints: {
            prev: 'Previous $0',
            next: 'Next $0',
            today: 'This $0',
        },
        viewHint: '$0 view',
        navLinkHint: 'Go to $0',
        moreLinkHint(eventCnt) {
            return `Show ${eventCnt} more event${eventCnt === 1 ? '' : 's'}`;
        },
    };

    var l21 = {
        code: 'en-nz',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonHints: {
            prev: 'Previous $0',
            next: 'Next $0',
            today: 'This $0',
        },
        viewHint: '$0 view',
        navLinkHint: 'Go to $0',
        moreLinkHint(eventCnt) {
            return `Show ${eventCnt} more event${eventCnt === 1 ? '' : 's'}`;
        },
    };

    var l22 = {
        code: 'eo',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Antaŭa',
            next: 'Sekva',
            today: 'Hodiaŭ',
            year: 'Jaro',
            month: 'Monato',
            week: 'Semajno',
            day: 'Tago',
            list: 'Tagordo',
        },
        weekText: 'Sm',
        allDayText: 'Tuta tago',
        moreLinkText: 'pli',
        noEventsText: 'Neniuj eventoj por montri',
    };

    var l23 = {
        code: 'es',
        week: {
            dow: 0,
            doy: 6, // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: 'Ant',
            next: 'Sig',
            today: 'Hoy',
            year: 'Año',
            month: 'Mes',
            week: 'Semana',
            day: 'Día',
            list: 'Agenda',
        },
        weekText: 'Sm',
        allDayText: 'Todo el día',
        moreLinkText: 'más',
        noEventsText: 'No hay eventos para mostrar',
    };

    var l24 = {
        code: 'es',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Ant',
            next: 'Sig',
            today: 'Hoy',
            year: 'Año',
            month: 'Mes',
            week: 'Semana',
            day: 'Día',
            list: 'Agenda',
        },
        buttonHints: {
            prev: '$0 antes',
            next: '$0 siguiente',
            today(buttonText) {
                return (buttonText === 'Día') ? 'Hoy' :
                    ((buttonText === 'Semana') ? 'Esta' : 'Este') + ' ' + buttonText.toLocaleLowerCase();
            },
        },
        viewHint(buttonText) {
            return 'Vista ' + (buttonText === 'Semana' ? 'de la' : 'del') + ' ' + buttonText.toLocaleLowerCase();
        },
        weekText: 'Sm',
        weekTextLong: 'Semana',
        allDayText: 'Todo el día',
        moreLinkText: 'más',
        moreLinkHint(eventCnt) {
            return `Mostrar ${eventCnt} eventos más`;
        },
        noEventsText: 'No hay eventos para mostrar',
        navLinkHint: 'Ir al $0',
        closeHint: 'Cerrar',
        timeHint: 'La hora',
        eventHint: 'Evento',
    };

    var l25 = {
        code: 'et',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Eelnev',
            next: 'Järgnev',
            today: 'Täna',
            year: 'Aasta',
            month: 'Kuu',
            week: 'Nädal',
            day: 'Päev',
            list: 'Päevakord',
        },
        weekText: 'näd',
        allDayText: 'Kogu päev',
        moreLinkText(n) {
            return '+ veel ' + n;
        },
        noEventsText: 'Kuvamiseks puuduvad sündmused',
    };

    var l26 = {
        code: 'eu',
        week: {
            dow: 1,
            doy: 7, // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: 'Aur',
            next: 'Hur',
            today: 'Gaur',
            year: 'Urtea',
            month: 'Hilabetea',
            week: 'Astea',
            day: 'Eguna',
            list: 'Agenda',
        },
        weekText: 'As',
        allDayText: 'Egun osoa',
        moreLinkText: 'gehiago',
        noEventsText: 'Ez dago ekitaldirik erakusteko',
    };

    var l27 = {
        code: 'fa',
        week: {
            dow: 6,
            doy: 12, // The week that contains Jan 1st is the first week of the year.
        },
        direction: 'rtl',
        buttonText: {
            prev: 'قبلی',
            next: 'بعدی',
            today: 'امروز',
            year: 'سال',
            month: 'ماه',
            week: 'هفته',
            day: 'روز',
            list: 'برنامه',
        },
        weekText: 'هف',
        allDayText: 'تمام روز',
        moreLinkText(n) {
            return 'بیش از ' + n;
        },
        noEventsText: 'هیچ رویدادی به نمایش',
    };

    var l28 = {
        code: 'fi',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Edellinen',
            next: 'Seuraava',
            today: 'Tänään',
            year: 'Vuosi',
            month: 'Kuukausi',
            week: 'Viikko',
            day: 'Päivä',
            list: 'Tapahtumat',
        },
        weekText: 'Vk',
        allDayText: 'Koko päivä',
        moreLinkText: 'lisää',
        noEventsText: 'Ei näytettäviä tapahtumia',
    };

    var l29 = {
        code: 'fr',
        buttonText: {
            prev: 'Précédent',
            next: 'Suivant',
            today: 'Aujourd\'hui',
            year: 'Année',
            month: 'Mois',
            week: 'Semaine',
            day: 'Jour',
            list: 'Mon planning',
        },
        weekText: 'Sem.',
        allDayText: 'Toute la journée',
        moreLinkText: 'en plus',
        noEventsText: 'Aucun évènement à afficher',
    };

    var l30 = {
        code: 'fr-ch',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Précédent',
            next: 'Suivant',
            today: 'Courant',
            year: 'Année',
            month: 'Mois',
            week: 'Semaine',
            day: 'Jour',
            list: 'Mon planning',
        },
        weekText: 'Sm',
        allDayText: 'Toute la journée',
        moreLinkText: 'en plus',
        noEventsText: 'Aucun évènement à afficher',
    };

    var l31 = {
        code: 'fr',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Précédent',
            next: 'Suivant',
            today: 'Aujourd\'hui',
            year: 'Année',
            month: 'Mois',
            week: 'Semaine',
            day: 'Jour',
            list: 'Planning',
        },
        weekText: 'Sem.',
        weekTextLong: 'Semaine',
        allDayText: 'Toute la journée',
        moreLinkText: 'en plus',
        noEventsText: 'Aucun évènement à afficher',
    };

    var l32 = {
        code: 'gl',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Ant',
            next: 'Seg',
            today: 'Hoxe',
            year: 'Ano',
            month: 'Mes',
            week: 'Semana',
            day: 'Día',
            list: 'Axenda',
        },
        buttonHints: {
            prev: '$0 antes',
            next: '$0 seguinte',
            today(buttonText) {
                return (buttonText === 'Día') ? 'Hoxe' :
                    ((buttonText === 'Semana') ? 'Esta' : 'Este') + ' ' + buttonText.toLocaleLowerCase();
            },
        },
        viewHint(buttonText) {
            return 'Vista ' + (buttonText === 'Semana' ? 'da' : 'do') + ' ' + buttonText.toLocaleLowerCase();
        },
        weekText: 'Sm',
        weekTextLong: 'Semana',
        allDayText: 'Todo o día',
        moreLinkText: 'máis',
        moreLinkHint(eventCnt) {
            return `Amosar ${eventCnt} eventos máis`;
        },
        noEventsText: 'Non hai eventos para amosar',
        navLinkHint: 'Ir ao $0',
        closeHint: 'Pechar',
        timeHint: 'A hora',
        eventHint: 'Evento',
    };

    var l33 = {
        code: 'he',
        direction: 'rtl',
        buttonText: {
            prev: 'הקודם',
            next: 'הבא',
            today: 'היום',
            year: 'שנה',
            month: 'חודש',
            week: 'שבוע',
            day: 'יום',
            list: 'סדר יום',
        },
        allDayText: 'כל היום',
        moreLinkText: 'נוספים',
        noEventsText: 'אין אירועים להצגה',
        weekText: 'שבוע',
    };

    var l34 = {
        code: 'hi',
        week: {
            dow: 0,
            doy: 6, // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: 'पिछला',
            next: 'अगला',
            today: 'आज',
            year: 'वर्ष',
            month: 'महीना',
            week: 'सप्ताह',
            day: 'दिन',
            list: 'कार्यसूची',
        },
        weekText: 'हफ्ता',
        allDayText: 'सभी दिन',
        moreLinkText(n) {
            return '+अधिक ' + n;
        },
        noEventsText: 'कोई घटनाओं को प्रदर्शित करने के लिए',
    };

    var l35 = {
        code: 'hr',
        week: {
            dow: 1,
            doy: 7, // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: 'Prijašnji',
            next: 'Sljedeći',
            today: 'Danas',
            year: 'Godina',
            month: 'Mjesec',
            week: 'Tjedan',
            day: 'Dan',
            list: 'Raspored',
        },
        weekText: 'Tje',
        allDayText: 'Cijeli dan',
        moreLinkText(n) {
            return '+ još ' + n;
        },
        noEventsText: 'Nema događaja za prikaz',
    };

    var l36 = {
        code: 'hu',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'vissza',
            next: 'előre',
            today: 'ma',
            year: 'Év',
            month: 'Hónap',
            week: 'Hét',
            day: 'Nap',
            list: 'Lista',
        },
        weekText: 'Hét',
        allDayText: 'Egész nap',
        moreLinkText: 'további',
        noEventsText: 'Nincs megjeleníthető esemény',
    };

    var l37 = {
        code: 'hy-am',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Նախորդ',
            next: 'Հաջորդ',
            today: 'Այսօր',
            year: 'Տարի',
            month: 'Ամիս',
            week: 'Շաբաթ',
            day: 'Օր',
            list: 'Օրվա ցուցակ',
        },
        weekText: 'Շաբ',
        allDayText: 'Ամբողջ օր',
        moreLinkText(n) {
            return '+ ևս ' + n;
        },
        noEventsText: 'Բացակայում է իրադարձությունը ցուցադրելու',
    };

    var l38 = {
        code: 'id',
        week: {
            dow: 1,
            doy: 7, // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: 'mundur',
            next: 'maju',
            today: 'hari ini',
            year: 'Tahun',
            month: 'Bulan',
            week: 'Minggu',
            day: 'Hari',
            list: 'Agenda',
        },
        weekText: 'Mg',
        allDayText: 'Sehari penuh',
        moreLinkText: 'lebih',
        noEventsText: 'Tidak ada acara untuk ditampilkan',
    };

    var l39 = {
        code: 'is',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Fyrri',
            next: 'Næsti',
            today: 'Í dag',
            year: 'Ár',
            month: 'Mánuður',
            week: 'Vika',
            day: 'Dagur',
            list: 'Dagskrá',
        },
        weekText: 'Vika',
        allDayText: 'Allan daginn',
        moreLinkText: 'meira',
        noEventsText: 'Engir viðburðir til að sýna',
    };

    var l40 = {
        code: 'it',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Prec',
            next: 'Succ',
            today: 'Oggi',
            year: 'Anno',
            month: 'Mese',
            week: 'Settimana',
            day: 'Giorno',
            list: 'Agenda',
        },
        weekText: 'Sm',
        allDayText: 'Tutto il giorno',
        moreLinkText(n) {
            return '+altri ' + n;
        },
        noEventsText: 'Non ci sono eventi da visualizzare',
    };

    var l41 = {
        code: 'ja',
        buttonText: {
            prev: '前',
            next: '次',
            today: '今日',
            year: '年',
            month: '月',
            week: '週',
            day: '日',
            list: '予定リスト',
        },
        weekText: '週',
        allDayText: '終日',
        moreLinkText(n) {
            return '他 ' + n + ' 件';
        },
        noEventsText: '表示する予定はありません',
    };

    var l42 = {
        code: 'ka',
        week: {
            dow: 1,
            doy: 7,
        },
        buttonText: {
            prev: 'წინა',
            next: 'შემდეგი',
            today: 'დღეს',
            year: 'წელიწადი',
            month: 'თვე',
            week: 'კვირა',
            day: 'დღე',
            list: 'დღის წესრიგი',
        },
        weekText: 'კვ',
        allDayText: 'მთელი დღე',
        moreLinkText(n) {
            return '+ კიდევ ' + n;
        },
        noEventsText: 'ღონისძიებები არ არის',
    };

    var l43 = {
        code: 'kk',
        week: {
            dow: 1,
            doy: 7, // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: 'Алдыңғы',
            next: 'Келесі',
            today: 'Бүгін',
            year: 'Жыл',
            month: 'Ай',
            week: 'Апта',
            day: 'Күн',
            list: 'Күн тәртібі',
        },
        weekText: 'Не',
        allDayText: 'Күні бойы',
        moreLinkText(n) {
            return '+ тағы ' + n;
        },
        noEventsText: 'Көрсету үшін оқиғалар жоқ',
    };

    var l44 = {
        code: 'km',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'មុន',
            next: 'បន្ទាប់',
            today: 'ថ្ងៃនេះ',
            year: 'ឆ្នាំ',
            month: 'ខែ',
            week: 'សប្តាហ៍',
            day: 'ថ្ងៃ',
            list: 'បញ្ជី',
        },
        weekText: 'សប្តាហ៍',
        allDayText: 'ពេញមួយថ្ងៃ',
        moreLinkText: 'ច្រើនទៀត',
        noEventsText: 'គ្មានព្រឹត្តិការណ៍ត្រូវបង្ហាញ',
    };

    var l45 = {
        code: 'ko',
        buttonText: {
            prev: '이전달',
            next: '다음달',
            today: '오늘',
            year: '년도',
            month: '월',
            week: '주',
            day: '일',
            list: '일정목록',
        },
        weekText: '주',
        allDayText: '종일',
        moreLinkText: '개',
        noEventsText: '일정이 없습니다',
    };

    var l46 = {
        code: 'ku',
        week: {
            dow: 6,
            doy: 12, // The week that contains Jan 1st is the first week of the year.
        },
        direction: 'rtl',
        buttonText: {
            prev: 'پێشتر',
            next: 'دواتر',
            today: 'ئەمڕو',
            year: 'ساڵ',
            month: 'مانگ',
            week: 'هەفتە',
            day: 'ڕۆژ',
            list: 'بەرنامە',
        },
        weekText: 'هەفتە',
        allDayText: 'هەموو ڕۆژەکە',
        moreLinkText: 'زیاتر',
        noEventsText: 'هیچ ڕووداوێك نیە',
    };

    var l47 = {
        code: 'lb',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Zréck',
            next: 'Weider',
            today: 'Haut',
            year: 'Joer',
            month: 'Mount',
            week: 'Woch',
            day: 'Dag',
            list: 'Terminiwwersiicht',
        },
        weekText: 'W',
        allDayText: 'Ganzen Dag',
        moreLinkText: 'méi',
        noEventsText: 'Nee Evenementer ze affichéieren',
    };

    var l48 = {
        code: 'lt',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Atgal',
            next: 'Pirmyn',
            today: 'Šiandien',
            year: 'Metai',
            month: 'Mėnuo',
            week: 'Savaitė',
            day: 'Diena',
            list: 'Darbotvarkė',
        },
        weekText: 'SAV',
        allDayText: 'Visą dieną',
        moreLinkText: 'daugiau',
        noEventsText: 'Nėra įvykių rodyti',
    };

    var l49 = {
        code: 'lv',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Iepr.',
            next: 'Nāk.',
            today: 'Šodien',
            year: 'Gads',
            month: 'Mēnesis',
            week: 'Nedēļa',
            day: 'Diena',
            list: 'Dienas kārtība',
        },
        weekText: 'Ned.',
        allDayText: 'Visu dienu',
        moreLinkText(n) {
            return '+vēl ' + n;
        },
        noEventsText: 'Nav notikumu',
    };

    var l50 = {
        code: 'mk',
        buttonText: {
            prev: 'претходно',
            next: 'следно',
            today: 'Денес',
            year: 'година',
            month: 'Месец',
            week: 'Недела',
            day: 'Ден',
            list: 'График',
        },
        weekText: 'Сед',
        allDayText: 'Цел ден',
        moreLinkText(n) {
            return '+повеќе ' + n;
        },
        noEventsText: 'Нема настани за прикажување',
    };

    var l51 = {
        code: 'ms',
        week: {
            dow: 1,
            doy: 7, // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: 'Sebelum',
            next: 'Selepas',
            today: 'hari ini',
            year: 'Tahun',
            month: 'Bulan',
            week: 'Minggu',
            day: 'Hari',
            list: 'Agenda',
        },
        weekText: 'Mg',
        allDayText: 'Sepanjang hari',
        moreLinkText(n) {
            return 'masih ada ' + n + ' acara';
        },
        noEventsText: 'Tiada peristiwa untuk dipaparkan',
    };

    var l52 = {
        code: 'nb',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Forrige',
            next: 'Neste',
            today: 'I dag',
            year: 'År',
            month: 'Måned',
            week: 'Uke',
            day: 'Dag',
            list: 'Agenda',
        },
        weekText: 'Uke',
        weekTextLong: 'Uke',
        allDayText: 'Hele dagen',
        moreLinkText: 'til',
        noEventsText: 'Ingen hendelser å vise',
        buttonHints: {
            prev: 'Forrige $0',
            next: 'Neste $0',
            today: 'Nåværende $0',
        },
        viewHint: '$0 visning',
        navLinkHint: 'Gå til $0',
        moreLinkHint(eventCnt) {
            return `Vis ${eventCnt} flere hendelse${eventCnt === 1 ? '' : 'r'}`;
        },
    };

    var l53 = {
        code: 'ne',
        week: {
            dow: 7,
            doy: 1, // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: 'अघिल्लो',
            next: 'अर्को',
            today: 'आज',
            year: 'वर्ष',
            month: 'महिना',
            week: 'हप्ता',
            day: 'दिन',
            list: 'सूची',
        },
        weekText: 'हप्ता',
        allDayText: 'दिनभरि',
        moreLinkText: 'थप लिंक',
        noEventsText: 'देखाउनको लागि कुनै घटनाहरू छैनन्',
    };

    var l54 = {
        code: 'nl',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Vorige',
            next: 'Volgende',
            today: 'Vandaag',
            year: 'Jaar',
            month: 'Maand',
            week: 'Week',
            day: 'Dag',
            list: 'Lijst',
        },
        allDayText: 'Hele dag',
        moreLinkText: 'extra',
        noEventsText: 'Geen evenementen om te laten zien',
    };

    var l55 = {
        code: 'nn',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Førre',
            next: 'Neste',
            today: 'I dag',
            year: 'År',
            month: 'Månad',
            week: 'Veke',
            day: 'Dag',
            list: 'Agenda',
        },
        weekText: 'Veke',
        allDayText: 'Heile dagen',
        moreLinkText: 'til',
        noEventsText: 'Ingen hendelser å vise',
    };

    var l56 = {
        code: 'pl',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Poprzedni',
            next: 'Następny',
            today: 'Dziś',
            year: 'Rok',
            month: 'Miesiąc',
            week: 'Tydzień',
            day: 'Dzień',
            list: 'Plan dnia',
        },
        weekText: 'Tydz',
        allDayText: 'Cały dzień',
        moreLinkText: 'więcej',
        noEventsText: 'Brak wydarzeń do wyświetlenia',
    };

    var l57 = {
        code: 'pt-br',
        buttonText: {
            prev: 'Anterior',
            next: 'Próximo',
            prevYear: 'Ano anterior',
            nextYear: 'Próximo ano',
            year: 'Ano',
            today: 'Hoje',
            month: 'Mês',
            week: 'Semana',
            day: 'Dia',
            list: 'Lista',
        },
        buttonHints: {
            prev: '$0 Anterior',
            next: 'Próximo $0',
            today(buttonText) {
                return (buttonText === 'Dia') ? 'Hoje' :
                    ((buttonText === 'Semana') ? 'Esta' : 'Este') + ' ' + buttonText.toLocaleLowerCase();
            },
        },
        viewHint(buttonText) {
            return 'Visualizar ' + (buttonText === 'Semana' ? 'a' : 'o') + ' ' + buttonText.toLocaleLowerCase();
        },
        weekText: 'Sm',
        weekTextLong: 'Semana',
        allDayText: 'dia inteiro',
        moreLinkText(n) {
            return 'mais +' + n;
        },
        moreLinkHint(eventCnt) {
            return `Mostrar mais ${eventCnt} eventos`;
        },
        noEventsText: 'Não há eventos para mostrar',
        navLinkHint: 'Ir para $0',
        closeHint: 'Fechar',
        timeHint: 'A hora',
        eventHint: 'Evento',
    };

    var l58 = {
        code: 'pt',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Anterior',
            next: 'Seguinte',
            today: 'Hoje',
            year: 'Ano',
            month: 'Mês',
            week: 'Semana',
            day: 'Dia',
            list: 'Agenda',
        },
        weekText: 'Sem',
        allDayText: 'Todo o dia',
        moreLinkText: 'mais',
        noEventsText: 'Não há eventos para mostrar',
    };

    var l59 = {
        code: 'ro',
        week: {
            dow: 1,
            doy: 7, // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: 'precedentă',
            next: 'următoare',
            today: 'Azi',
            year: 'An',
            month: 'Lună',
            week: 'Săptămână',
            day: 'Zi',
            list: 'Agendă',
        },
        weekText: 'Săpt',
        allDayText: 'Toată ziua',
        moreLinkText(n) {
            return '+alte ' + n;
        },
        noEventsText: 'Nu există evenimente de afișat',
    };

    var l60 = {
        code: 'ru',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Пред',
            next: 'След',
            today: 'Сегодня',
            year: 'Год',
            month: 'Месяц',
            week: 'Неделя',
            day: 'День',
            list: 'Повестка дня',
        },
        weekText: 'Нед',
        allDayText: 'Весь день',
        moreLinkText(n) {
            return '+ ещё ' + n;
        },
        noEventsText: 'Нет событий для отображения',
    };

    var l61 = {
        code: 'si-lk',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'පෙර',
            next: 'පසු',
            today: 'අද',
            year: 'අවුරුදු',
            month: 'මාසය',
            week: 'සතිය',
            day: 'දවස',
            list: 'ලැයිස්තුව',
        },
        weekText: 'සති',
        allDayText: 'සියලු',
        moreLinkText: 'තවත්',
        noEventsText: 'මුකුත් නැත',
    };

    var l62 = {
        code: 'sk',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Predchádzajúci',
            next: 'Nasledujúci',
            today: 'Dnes',
            year: 'Rok',
            month: 'Mesiac',
            week: 'Týždeň',
            day: 'Deň',
            list: 'Rozvrh',
        },
        weekText: 'Ty',
        allDayText: 'Celý deň',
        moreLinkText(n) {
            return '+ďalšie: ' + n;
        },
        noEventsText: 'Žiadne akcie na zobrazenie',
    };

    var l63 = {
        code: 'sl',
        week: {
            dow: 1,
            doy: 7, // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: 'Prejšnji',
            next: 'Naslednji',
            today: 'Trenutni',
            year: 'Leto',
            month: 'Mesec',
            week: 'Teden',
            day: 'Dan',
            list: 'Dnevni red',
        },
        weekText: 'Teden',
        allDayText: 'Ves dan',
        moreLinkText: 'več',
        noEventsText: 'Ni dogodkov za prikaz',
    };

    var l64 = {
        code: 'sm',
        buttonText: {
            prev: 'Talu ai',
            next: 'Mulimuli atu',
            today: 'Aso nei',
            year: 'Tausaga',
            month: 'Masina',
            week: 'Vaiaso',
            day: 'Aso',
            list: 'Faasologa',
        },
        weekText: 'Vaiaso',
        allDayText: 'Aso atoa',
        moreLinkText: 'sili atu',
        noEventsText: 'Leai ni mea na tutupu',
    };

    var l65 = {
        code: 'sq',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'mbrapa',
            next: 'Përpara',
            today: 'Sot',
            year: 'Viti',
            month: 'Muaj',
            week: 'Javë',
            day: 'Ditë',
            list: 'Listë',
        },
        weekText: 'Ja',
        allDayText: 'Gjithë ditën',
        moreLinkText(n) {
            return '+më tepër ' + n;
        },
        noEventsText: 'Nuk ka evente për të shfaqur',
    };

    var l66 = {
        code: 'sr-cyrl',
        week: {
            dow: 1,
            doy: 7, // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: 'Претходна',
            next: 'следећи',
            today: 'Данас',
            year: 'Година',
            month: 'Месец',
            week: 'Недеља',
            day: 'Дан',
            list: 'Планер',
        },
        weekText: 'Сед',
        allDayText: 'Цео дан',
        moreLinkText(n) {
            return '+ још ' + n;
        },
        noEventsText: 'Нема догађаја за приказ',
    };

    var l67 = {
        code: 'sr',
        week: {
            dow: 1,
            doy: 7, // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: 'Prethodna',
            next: 'Sledeći',
            today: 'Danas',
            year: 'Godina',
            month: 'Mеsеc',
            week: 'Nеdеlja',
            day: 'Dan',
            list: 'Planеr',
        },
        weekText: 'Sed',
        allDayText: 'Cеo dan',
        moreLinkText(n) {
            return '+ još ' + n;
        },
        noEventsText: 'Nеma događaja za prikaz',
    };

    var l68 = {
        code: 'sv',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Förra',
            next: 'Nästa',
            today: 'Idag',
            year: 'År',
            month: 'Månad',
            week: 'Vecka',
            day: 'Dag',
            list: 'Program',
        },
        buttonHints: {
            prev(buttonText) {
                return `Föregående ${buttonText.toLocaleLowerCase()}`;
            },
            next(buttonText) {
                return `Nästa ${buttonText.toLocaleLowerCase()}`;
            },
            today(buttonText) {
                return (buttonText === 'Program' ? 'Detta' : 'Denna') + ' ' + buttonText.toLocaleLowerCase();
            },
        },
        viewHint: '$0 vy',
        navLinkHint: 'Gå till $0',
        moreLinkHint(eventCnt) {
            return `Visa ytterligare ${eventCnt} händelse${eventCnt === 1 ? '' : 'r'}`;
        },
        weekText: 'v.',
        weekTextLong: 'Vecka',
        allDayText: 'Heldag',
        moreLinkText: 'till',
        noEventsText: 'Inga händelser att visa',
        closeHint: 'Stäng',
        timeHint: 'Klockan',
        eventHint: 'Händelse',
    };

    var l69 = {
        code: 'ta-in',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'முந்தைய',
            next: 'அடுத்தது',
            today: 'இன்று',
            year: 'ஆண்டு',
            month: 'மாதம்',
            week: 'வாரம்',
            day: 'நாள்',
            list: 'தினசரி அட்டவணை',
        },
        weekText: 'வாரம்',
        allDayText: 'நாள் முழுவதும்',
        moreLinkText(n) {
            return '+ மேலும் ' + n;
        },
        noEventsText: 'காண்பிக்க நிகழ்வுகள் இல்லை',
    };

    var l70 = {
        code: 'th',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'ก่อนหน้า',
            next: 'ถัดไป',
            prevYear: 'ปีก่อนหน้า',
            nextYear: 'ปีถัดไป',
            year: 'ปี',
            today: 'วันนี้',
            month: 'เดือน',
            week: 'สัปดาห์',
            day: 'วัน',
            list: 'กำหนดการ',
        },
        weekText: 'สัปดาห์',
        allDayText: 'ตลอดวัน',
        moreLinkText: 'เพิ่มเติม',
        noEventsText: 'ไม่มีกิจกรรมที่จะแสดง',
    };

    var l71 = {
        code: 'tr',
        week: {
            dow: 1,
            doy: 7, // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: 'geri',
            next: 'ileri',
            today: 'bugün',
            year: 'Yıl',
            month: 'Ay',
            week: 'Hafta',
            day: 'Gün',
            list: 'Ajanda',
        },
        weekText: 'Hf',
        allDayText: 'Tüm gün',
        moreLinkText: 'daha fazla',
        noEventsText: 'Gösterilecek etkinlik yok',
    };

    var l72 = {
        code: 'ug',
        buttonText: {
            prev: 'ئالدىنقى',
            next: 'كېيىنكى',
            today: 'بۈگۈن',
            year: 'يىل',
            month: 'ئاي',
            week: 'ھەپتە',
            day: 'كۈن',
            list: 'كۈنتەرتىپ',
        },
        allDayText: 'پۈتۈن كۈن',
    };

    var l73 = {
        code: 'uk',
        week: {
            dow: 1,
            doy: 7, // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: 'Попередній',
            next: 'далі',
            today: 'Сьогодні',
            year: 'рік',
            month: 'Місяць',
            week: 'Тиждень',
            day: 'День',
            list: 'Порядок денний',
        },
        weekText: 'Тиж',
        allDayText: 'Увесь день',
        moreLinkText(n) {
            return '+ще ' + n + '...';
        },
        noEventsText: 'Немає подій для відображення',
    };

    var l74 = {
        code: 'uz-cy',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Олин',
            next: 'Кейин',
            today: 'Бугун',
            month: 'Ой',
            week: 'Ҳафта',
            day: 'Кун',
            list: 'Кун тартиби',
        },
        weekText: 'Ҳафта',
        allDayText: 'Кун бўйича',
        moreLinkText(n) {
            return '+ яна ' + n;
        },
        noEventsText: 'Кўрсатиш учун воқеалар йўқ',
    };

    var l75 = {
        code: 'uz',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Oldingi',
            next: 'Keyingi',
            today: 'Bugun',
            year: 'Yil',
            month: 'Oy',
            week: 'Xafta',
            day: 'Kun',
            list: 'Kun tartibi',
        },
        allDayText: 'Kun bo\'yi',
        moreLinkText(n) {
            return '+ yana ' + n;
        },
        noEventsText: 'Ko\'rsatish uchun voqealar yo\'q',
    };

    var l76 = {
        code: 'vi',
        week: {
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: 'Trước',
            next: 'Tiếp',
            today: 'Hôm nay',
            year: 'Năm',
            month: 'Tháng',
            week: 'Tuần',
            day: 'Ngày',
            list: 'Lịch biểu',
        },
        weekText: 'Tu',
        allDayText: 'Cả ngày',
        moreLinkText(n) {
            return '+ thêm ' + n;
        },
        noEventsText: 'Không có sự kiện để hiển thị',
    };

    var l77 = {
        code: 'zh-cn',
        week: {
            // GB/T 7408-1994《数据元和交换格式·信息交换·日期和时间表示法》与ISO 8601:1988等效
            dow: 1,
            doy: 4, // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: '上月',
            next: '下月',
            today: '今天',
            year: '年',
            month: '月',
            week: '周',
            day: '日',
            list: '日程',
        },
        weekText: '周',
        allDayText: '全天',
        moreLinkText(n) {
            return '另外 ' + n + ' 个';
        },
        noEventsText: '没有事件显示',
    };

    var l78 = {
        code: 'zh-tw',
        buttonText: {
            prev: '上個',
            next: '下個',
            today: '今天',
            year: '年',
            month: '月',
            week: '週',
            day: '天',
            list: '活動列表',
        },
        weekText: '週',
        allDayText: '整天',
        moreLinkText: '顯示更多',
        noEventsText: '沒有任何活動',
    };

    var localesAll = [
      l0, l1, l2, l3, l4, l5, l6, l7, l8, l9, l10, l11, l12, l13, l14, l15, l16, l17, l18, l19, l20, l21, l22, l23, l24, l25, l26, l27, l28, l29, l30, l31, l32, l33, l34, l35, l36, l37, l38, l39, l40, l41, l42, l43, l44, l45, l46, l47, l48, l49, l50, l51, l52, l53, l54, l55, l56, l57, l58, l59, l60, l61, l62, l63, l64, l65, l66, l67, l68, l69, l70, l71, l72, l73, l74, l75, l76, l77, l78, 
    ];

    index_js.globalLocales.push(...localesAll);

})(FullCalendar);
