(function (global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined' ? module.exports = factory() :
    typeof define === 'function' && define.amd ? define(factory) :
    (global = global || self, global.FullCalendarLocalesAll = factory());
}(this, function () { 'use strict';

    var _m0 = {
        code: "af",
        week: {
            dow: 1,
            doy: 4 // Die week wat die 4de Januarie bevat is die eerste week van die jaar.
        },
        buttonText: {
            prev: "Vorige",
            next: "Volgende",
            today: "Vandag",
            year: "Jaar",
            month: "Maand",
            week: "Week",
            day: "Dag",
            list: "Agenda"
        },
        allDayHtml: "Heeldag",
        eventLimitText: "Addisionele",
        noEventsMessage: "Daar is geen gebeurtenisse nie"
    };

    var _m1 = {
        code: "ar-dz",
        week: {
            dow: 0,
            doy: 4 // The week that contains Jan 1st is the first week of the year.
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

    var _m2 = {
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

    var _m3 = {
        code: "ar-ly",
        week: {
            dow: 6,
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

    var _m4 = {
        code: "ar-ma",
        week: {
            dow: 6,
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

    var _m5 = {
        code: "ar-sa",
        week: {
            dow: 0,
            doy: 6 // The week that contains Jan 1st is the first week of the year.
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

    var _m6 = {
        code: "ar-tn",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
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

    var _m7 = {
        code: "ar",
        week: {
            dow: 6,
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

    var _m8 = {
        code: "az",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Əvvəl",
            next: "Sonra",
            today: "Bu Gün",
            month: "Ay",
            week: "Həftə",
            day: "Gün",
            list: "Gündəm"
        },
        weekLabel: "Həftə",
        allDayText: "Bütün Gün",
        eventLimitText: function (n) {
            return "+ daha çox " + n;
        },
        noEventsMessage: "Göstərmək üçün hadisə yoxdur"
    };

    var _m9 = {
        code: "bg",
        week: {
            dow: 1,
            doy: 7 // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: "назад",
            next: "напред",
            today: "днес",
            month: "Месец",
            week: "Седмица",
            day: "Ден",
            list: "График"
        },
        allDayText: "Цял ден",
        eventLimitText: function (n) {
            return "+още " + n;
        },
        noEventsMessage: "Няма събития за показване"
    };

    var _m10 = {
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

    var _m11 = {
        code: "ca",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Anterior",
            next: "Següent",
            today: "Avui",
            month: "Mes",
            week: "Setmana",
            day: "Dia",
            list: "Agenda"
        },
        weekLabel: "Set",
        allDayText: "Tot el dia",
        eventLimitText: "més",
        noEventsMessage: "No hi ha esdeveniments per mostrar"
    };

    var _m12 = {
        code: "cs",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Dříve",
            next: "Později",
            today: "Nyní",
            month: "Měsíc",
            week: "Týden",
            day: "Den",
            list: "Agenda"
        },
        weekLabel: "Týd",
        allDayText: "Celý den",
        eventLimitText: function (n) {
            return "+další: " + n;
        },
        noEventsMessage: "Žádné akce k zobrazení"
    };

    var _m13 = {
        code: "da",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Forrige",
            next: "Næste",
            today: "I dag",
            month: "Måned",
            week: "Uge",
            day: "Dag",
            list: "Agenda"
        },
        weekLabel: "Uge",
        allDayText: "Hele dagen",
        eventLimitText: "flere",
        noEventsMessage: "Ingen arrangementer at vise"
    };

    var _m14 = {
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

    var _m15 = {
        code: "el",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4st is the first week of the year.
        },
        buttonText: {
            prev: "Προηγούμενος",
            next: "Επόμενος",
            today: "Σήμερα",
            month: "Μήνας",
            week: "Εβδομάδα",
            day: "Ημέρα",
            list: "Ατζέντα"
        },
        weekLabel: "Εβδ",
        allDayText: "Ολοήμερο",
        eventLimitText: "περισσότερα",
        noEventsMessage: "Δεν υπάρχουν γεγονότα προς εμφάνιση"
    };

    var _m16 = {
        code: "en-au",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        }
    };

    var _m17 = {
        code: "en-gb",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        }
    };

    var _m18 = {
        code: "en-nz",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        }
    };

    var _m19 = {
        code: "es",
        week: {
            dow: 0,
            doy: 6 // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: "Ant",
            next: "Sig",
            today: "Hoy",
            month: "Mes",
            week: "Semana",
            day: "Día",
            list: "Agenda"
        },
        weekLabel: "Sm",
        allDayHtml: "Todo<br/>el día",
        eventLimitText: "más",
        noEventsMessage: "No hay eventos para mostrar"
    };

    var _m20 = {
        code: "es",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Ant",
            next: "Sig",
            today: "Hoy",
            month: "Mes",
            week: "Semana",
            day: "Día",
            list: "Agenda"
        },
        weekLabel: "Sm",
        allDayHtml: "Todo<br/>el día",
        eventLimitText: "más",
        noEventsMessage: "No hay eventos para mostrar"
    };

    var _m21 = {
        code: "et",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Eelnev",
            next: "Järgnev",
            today: "Täna",
            month: "Kuu",
            week: "Nädal",
            day: "Päev",
            list: "Päevakord"
        },
        weekLabel: "näd",
        allDayText: "Kogu päev",
        eventLimitText: function (n) {
            return "+ veel " + n;
        },
        noEventsMessage: "Kuvamiseks puuduvad sündmused"
    };

    var _m22 = {
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

    var _m23 = {
        code: "fa",
        week: {
            dow: 6,
            doy: 12 // The week that contains Jan 1st is the first week of the year.
        },
        dir: 'rtl',
        buttonText: {
            prev: "قبلی",
            next: "بعدی",
            today: "امروز",
            month: "ماه",
            week: "هفته",
            day: "روز",
            list: "برنامه"
        },
        weekLabel: "هف",
        allDayText: "تمام روز",
        eventLimitText: function (n) {
            return "بیش از " + n;
        },
        noEventsMessage: "هیچ رویدادی به نمایش"
    };

    var _m24 = {
        code: "fi",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Edellinen",
            next: "Seuraava",
            today: "Tänään",
            month: "Kuukausi",
            week: "Viikko",
            day: "Päivä",
            list: "Tapahtumat"
        },
        weekLabel: "Vk",
        allDayText: "Koko päivä",
        eventLimitText: "lisää",
        noEventsMessage: "Ei näytettäviä tapahtumia"
    };

    var _m25 = {
        code: "fr",
        buttonText: {
            prev: "Précédent",
            next: "Suivant",
            today: "Aujourd'hui",
            year: "Année",
            month: "Mois",
            week: "Semaine",
            day: "Jour",
            list: "Mon planning"
        },
        weekLabel: "Sem.",
        allDayHtml: "Toute la<br/>journée",
        eventLimitText: "en plus",
        noEventsMessage: "Aucun événement à afficher"
    };

    var _m26 = {
        code: "fr-ch",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Précédent",
            next: "Suivant",
            today: "Courant",
            year: "Année",
            month: "Mois",
            week: "Semaine",
            day: "Jour",
            list: "Mon planning"
        },
        weekLabel: "Sm",
        allDayHtml: "Toute la<br/>journée",
        eventLimitText: "en plus",
        noEventsMessage: "Aucun événement à afficher"
    };

    var _m27 = {
        code: "fr",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Précédent",
            next: "Suivant",
            today: "Aujourd'hui",
            year: "Année",
            month: "Mois",
            week: "Semaine",
            day: "Jour",
            list: "Planning"
        },
        weekLabel: "Sem.",
        allDayHtml: "Toute la<br/>journée",
        eventLimitText: "en plus",
        noEventsMessage: "Aucun événement à afficher"
    };

    var _m28 = {
        code: "gl",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Ant",
            next: "Seg",
            today: "Hoxe",
            month: "Mes",
            week: "Semana",
            day: "Día",
            list: "Axenda"
        },
        weekLabel: "Sm",
        allDayHtml: "Todo<br/>o día",
        eventLimitText: "máis",
        noEventsMessage: "Non hai eventos para amosar"
    };

    var _m29 = {
        code: "he",
        dir: 'rtl',
        buttonText: {
            prev: "הקודם",
            next: "הבא",
            today: "היום",
            month: "חודש",
            week: "שבוע",
            day: "יום",
            list: "סדר יום"
        },
        allDayText: "כל היום",
        eventLimitText: "אחר",
        noEventsMessage: "אין אירועים להצגה",
        weekLabel: "שבוע"
    };

    var _m30 = {
        code: "hi",
        week: {
            dow: 0,
            doy: 6 // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: "पिछला",
            next: "अगला",
            today: "आज",
            month: "महीना",
            week: "सप्ताह",
            day: "दिन",
            list: "कार्यसूची"
        },
        weekLabel: "हफ्ता",
        allDayText: "सभी दिन",
        eventLimitText: function (n) {
            return "+अधिक " + n;
        },
        noEventsMessage: "कोई घटनाओं को प्रदर्शित करने के लिए"
    };

    var _m31 = {
        code: "hr",
        week: {
            dow: 1,
            doy: 7 // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: "Prijašnji",
            next: "Sljedeći",
            today: "Danas",
            month: "Mjesec",
            week: "Tjedan",
            day: "Dan",
            list: "Raspored"
        },
        weekLabel: "Tje",
        allDayText: "Cijeli dan",
        eventLimitText: function (n) {
            return "+ još " + n;
        },
        noEventsMessage: "Nema događaja za prikaz"
    };

    var _m32 = {
        code: "hu",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "vissza",
            next: "előre",
            today: "ma",
            month: "Hónap",
            week: "Hét",
            day: "Nap",
            list: "Napló"
        },
        weekLabel: "Hét",
        allDayText: "Egész nap",
        eventLimitText: "további",
        noEventsMessage: "Nincs megjeleníthető esemény"
    };

    var _m33 = {
        code: "id",
        week: {
            dow: 1,
            doy: 7 // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: "mundur",
            next: "maju",
            today: "hari ini",
            month: "Bulan",
            week: "Minggu",
            day: "Hari",
            list: "Agenda"
        },
        weekLabel: "Mg",
        allDayHtml: "Sehari<br/>penuh",
        eventLimitText: "lebih",
        noEventsMessage: "Tidak ada acara untuk ditampilkan"
    };

    var _m34 = {
        code: "is",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Fyrri",
            next: "Næsti",
            today: "Í dag",
            month: "Mánuður",
            week: "Vika",
            day: "Dagur",
            list: "Dagskrá"
        },
        weekLabel: "Vika",
        allDayHtml: "Allan<br/>daginn",
        eventLimitText: "meira",
        noEventsMessage: "Engir viðburðir til að sýna"
    };

    var _m35 = {
        code: "it",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Prec",
            next: "Succ",
            today: "Oggi",
            month: "Mese",
            week: "Settimana",
            day: "Giorno",
            list: "Agenda"
        },
        weekLabel: "Sm",
        allDayHtml: "Tutto il<br/>giorno",
        eventLimitText: function (n) {
            return "+altri " + n;
        },
        noEventsMessage: "Non ci sono eventi da visualizzare"
    };

    var _m36 = {
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

    var _m37 = {
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

    var _m38 = {
        code: "kk",
        week: {
            dow: 1,
            doy: 7 // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: "Алдыңғы",
            next: "Келесі",
            today: "Бүгін",
            month: "Ай",
            week: "Апта",
            day: "Күн",
            list: "Күн тәртібі"
        },
        weekLabel: "Не",
        allDayText: "Күні бойы",
        eventLimitText: function (n) {
            return "+ тағы " + n;
        },
        noEventsMessage: "Көрсету үшін оқиғалар жоқ"
    };

    var _m39 = {
        code: "ko",
        buttonText: {
            prev: "이전달",
            next: "다음달",
            today: "오늘",
            month: "월",
            week: "주",
            day: "일",
            list: "일정목록"
        },
        weekLabel: "주",
        allDayText: "종일",
        eventLimitText: "개",
        noEventsMessage: "일정이 없습니다"
    };

    var _m40 = {
        code: "lb",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Zréck",
            next: "Weider",
            today: "Haut",
            month: "Mount",
            week: "Woch",
            day: "Dag",
            list: "Terminiwwersiicht"
        },
        weekLabel: "W",
        allDayText: "Ganzen Dag",
        eventLimitText: "méi",
        noEventsMessage: "Nee Evenementer ze affichéieren"
    };

    var _m41 = {
        code: "lt",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Atgal",
            next: "Pirmyn",
            today: "Šiandien",
            month: "Mėnuo",
            week: "Savaitė",
            day: "Diena",
            list: "Darbotvarkė"
        },
        weekLabel: "SAV",
        allDayText: "Visą dieną",
        eventLimitText: "daugiau",
        noEventsMessage: "Nėra įvykių rodyti"
    };

    var _m42 = {
        code: "lv",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Iepr.",
            next: "Nāk.",
            today: "Šodien",
            month: "Mēnesis",
            week: "Nedēļa",
            day: "Diena",
            list: "Dienas kārtība"
        },
        weekLabel: "Ned.",
        allDayText: "Visu dienu",
        eventLimitText: function (n) {
            return "+vēl " + n;
        },
        noEventsMessage: "Nav notikumu"
    };

    var _m43 = {
        code: "mk",
        buttonText: {
            prev: "претходно",
            next: "следно",
            today: "Денес",
            month: "Месец",
            week: "Недела",
            day: "Ден",
            list: "График"
        },
        weekLabel: "Сед",
        allDayText: "Цел ден",
        eventLimitText: function (n) {
            return "+повеќе " + n;
        },
        noEventsMessage: "Нема настани за прикажување"
    };

    var _m44 = {
        code: "ms",
        week: {
            dow: 1,
            doy: 7 // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: "Sebelum",
            next: "Selepas",
            today: "hari ini",
            month: "Bulan",
            week: "Minggu",
            day: "Hari",
            list: "Agenda"
        },
        weekLabel: "Mg",
        allDayText: "Sepanjang hari",
        eventLimitText: function (n) {
            return "masih ada " + n + " acara";
        },
        noEventsMessage: "Tiada peristiwa untuk dipaparkan"
    };

    var _m45 = {
        code: "nb",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Forrige",
            next: "Neste",
            today: "I dag",
            month: "Måned",
            week: "Uke",
            day: "Dag",
            list: "Agenda"
        },
        weekLabel: "Uke",
        allDayText: "Hele dagen",
        eventLimitText: "til",
        noEventsMessage: "Ingen hendelser å vise"
    };

    var _m46 = {
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

    var _m47 = {
        code: "nn",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Førre",
            next: "Neste",
            today: "I dag",
            month: "Månad",
            week: "Veke",
            day: "Dag",
            list: "Agenda"
        },
        weekLabel: "Veke",
        allDayText: "Heile dagen",
        eventLimitText: "til",
        noEventsMessage: "Ingen hendelser å vise"
    };

    var _m48 = {
        code: "pl",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Poprzedni",
            next: "Następny",
            today: "Dziś",
            month: "Miesiąc",
            week: "Tydzień",
            day: "Dzień",
            list: "Plan dnia"
        },
        weekLabel: "Tydz",
        allDayText: "Cały dzień",
        eventLimitText: "więcej",
        noEventsMessage: "Brak wydarzeń do wyświetlenia"
    };

    var _m49 = {
        code: "pt-br",
        buttonText: {
            prev: "Anterior",
            next: "Próximo",
            today: "Hoje",
            month: "Mês",
            week: "Semana",
            day: "Dia",
            list: "Lista"
        },
        weekLabel: "Sm",
        allDayText: "dia inteiro",
        eventLimitText: function (n) {
            return "mais +" + n;
        },
        noEventsMessage: "Não há eventos para mostrar"
    };

    var _m50 = {
        code: "pt",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Anterior",
            next: "Seguinte",
            today: "Hoje",
            month: "Mês",
            week: "Semana",
            day: "Dia",
            list: "Agenda"
        },
        weekLabel: "Sem",
        allDayText: "Todo o dia",
        eventLimitText: "mais",
        noEventsMessage: "Não há eventos para mostrar"
    };

    var _m51 = {
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

    var _m52 = {
        code: "ru",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Пред",
            next: "След",
            today: "Сегодня",
            month: "Месяц",
            week: "Неделя",
            day: "День",
            list: "Повестка дня"
        },
        weekLabel: "Нед",
        allDayText: "Весь день",
        eventLimitText: function (n) {
            return "+ ещё " + n;
        },
        noEventsMessage: "Нет событий для отображения"
    };

    var _m53 = {
        code: "sk",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Predchádzajúci",
            next: "Nasledujúci",
            today: "Dnes",
            month: "Mesiac",
            week: "Týždeň",
            day: "Deň",
            list: "Rozvrh"
        },
        weekLabel: "Ty",
        allDayText: "Celý deň",
        eventLimitText: function (n) {
            return "+ďalšie: " + n;
        },
        noEventsMessage: "Žiadne akcie na zobrazenie"
    };

    var _m54 = {
        code: "sl",
        week: {
            dow: 1,
            doy: 7 // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: "Prejšnji",
            next: "Naslednji",
            today: "Trenutni",
            month: "Mesec",
            week: "Teden",
            day: "Dan",
            list: "Dnevni red"
        },
        weekLabel: "Teden",
        allDayText: "Ves dan",
        eventLimitText: "več",
        noEventsMessage: "Ni dogodkov za prikaz"
    };

    var _m55 = {
        code: "sq",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "mbrapa",
            next: "Përpara",
            today: "sot",
            month: "Muaj",
            week: "Javë",
            day: "Ditë",
            list: "Listë"
        },
        weekLabel: "Ja",
        allDayHtml: "Gjithë<br/>ditën",
        eventLimitText: function (n) {
            return "+më tepër " + n;
        },
        noEventsMessage: "Nuk ka evente për të shfaqur"
    };

    var _m56 = {
        code: "sr-cyrl",
        week: {
            dow: 1,
            doy: 7 // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: "Претходна",
            next: "следећи",
            today: "Данас",
            month: "Месец",
            week: "Недеља",
            day: "Дан",
            list: "Планер"
        },
        weekLabel: "Сед",
        allDayText: "Цео дан",
        eventLimitText: function (n) {
            return "+ још " + n;
        },
        noEventsMessage: "Нема догађаја за приказ"
    };

    var _m57 = {
        code: "sr",
        week: {
            dow: 1,
            doy: 7 // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: "Prethodna",
            next: "Sledeći",
            today: "Danas",
            month: "Mеsеc",
            week: "Nеdеlja",
            day: "Dan",
            list: "Planеr"
        },
        weekLabel: "Sed",
        allDayText: "Cеo dan",
        eventLimitText: function (n) {
            return "+ još " + n;
        },
        noEventsMessage: "Nеma događaja za prikaz"
    };

    var _m58 = {
        code: "sv",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Förra",
            next: "Nästa",
            today: "Idag",
            month: "Månad",
            week: "Vecka",
            day: "Dag",
            list: "Program"
        },
        weekLabel: "v.",
        allDayText: "Heldag",
        eventLimitText: "till",
        noEventsMessage: "Inga händelser att visa"
    };

    var _m59 = {
        code: "th",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "ก่อนหน้า",
            next: "ถัดไป",
            prevYear: 'ปีก่อนหน้า',
            nextYear: 'ปีถัดไป',
            year: 'ปี',
            today: "วันนี้",
            month: "เดือน",
            week: "สัปดาห์",
            day: "วัน",
            list: "กำหนดการ"
        },
        weekLabel: "สัปดาห์",
        allDayText: "ตลอดวัน",
        eventLimitText: "เพิ่มเติม",
        noEventsMessage: "ไม่มีกิจกรรมที่จะแสดง"
    };

    var _m60 = {
        code: "tr",
        week: {
            dow: 1,
            doy: 7 // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: "geri",
            next: "ileri",
            today: "bugün",
            month: "Ay",
            week: "Hafta",
            day: "Gün",
            list: "Ajanda"
        },
        weekLabel: "Hf",
        allDayText: "Tüm gün",
        eventLimitText: "daha fazla",
        noEventsMessage: "Gösterilecek etkinlik yok"
    };

    var _m61 = {
        code: "ug",
        buttonText: {
            month: "ئاي",
            week: "ھەپتە",
            day: "كۈن",
            list: "كۈنتەرتىپ"
        },
        allDayText: "پۈتۈن كۈن"
    };

    var _m62 = {
        code: "uk",
        week: {
            dow: 1,
            doy: 7 // The week that contains Jan 1st is the first week of the year.
        },
        buttonText: {
            prev: "Попередній",
            next: "далі",
            today: "Сьогодні",
            month: "Місяць",
            week: "Тиждень",
            day: "День",
            list: "Порядок денний"
        },
        weekLabel: "Тиж",
        allDayText: "Увесь день",
        eventLimitText: function (n) {
            return "+ще " + n + "...";
        },
        noEventsMessage: "Немає подій для відображення"
    };

    var _m63 = {
        code: "uz",
        buttonText: {
            month: "Oy",
            week: "Xafta",
            day: "Kun",
            list: "Kun tartibi"
        },
        allDayText: "Kun bo'yi",
        eventLimitText: function (n) {
            return "+ yana " + n;
        },
        noEventsMessage: "Ko'rsatish uchun voqealar yo'q"
    };

    var _m64 = {
        code: "vi",
        week: {
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "Trước",
            next: "Tiếp",
            today: "Hôm nay",
            month: "Tháng",
            week: "Tuần",
            day: "Ngày",
            list: "Lịch biểu"
        },
        weekLabel: "Tu",
        allDayText: "Cả ngày",
        eventLimitText: function (n) {
            return "+ thêm " + n;
        },
        noEventsMessage: "Không có sự kiện để hiển thị"
    };

    var _m65 = {
        code: "zh-cn",
        week: {
            // GB/T 7408-1994《数据元和交换格式·信息交换·日期和时间表示法》与ISO 8601:1988等效
            dow: 1,
            doy: 4 // The week that contains Jan 4th is the first week of the year.
        },
        buttonText: {
            prev: "上月",
            next: "下月",
            today: "今天",
            month: "月",
            week: "周",
            day: "日",
            list: "日程"
        },
        weekLabel: "周",
        allDayText: "全天",
        eventLimitText: function (n) {
            return "另外 " + n + " 个";
        },
        noEventsMessage: "没有事件显示"
    };

    var _m66 = {
        code: "zh-tw",
        buttonText: {
            prev: "上月",
            next: "下月",
            today: "今天",
            month: "月",
            week: "週",
            day: "天",
            list: "活動列表"
        },
        weekLabel: "周",
        allDayText: "整天",
        eventLimitText: '顯示更多',
        noEventsMessage: "没有任何活動"
    };

    var _rollupPluginMultiEntry_entryPoint = [
    _m0, _m1, _m2, _m3, _m4, _m5, _m6, _m7, _m8, _m9, _m10, _m11, _m12, _m13, _m14, _m15, _m16, _m17, _m18, _m19, _m20, _m21, _m22, _m23, _m24, _m25, _m26, _m27, _m28, _m29, _m30, _m31, _m32, _m33, _m34, _m35, _m36, _m37, _m38, _m39, _m40, _m41, _m42, _m43, _m44, _m45, _m46, _m47, _m48, _m49, _m50, _m51, _m52, _m53, _m54, _m55, _m56, _m57, _m58, _m59, _m60, _m61, _m62, _m63, _m64, _m65, _m66
    ];

    return _rollupPluginMultiEntry_entryPoint;

}));
