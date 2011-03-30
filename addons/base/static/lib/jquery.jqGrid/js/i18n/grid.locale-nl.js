(function(a) {
    a.jgrid =
    {
        defaults:
        {
            recordtext: "regels {0} - {1} van {2}",
            emptyrecords: "Geen data gevonden.",
            loadtext: "laden...",
            pgtext: "pagina  {0}  van {1}"
        },
        search:
        {
            caption: "Zoeken...",
            Find: "Zoek",
            Reset: "Herstellen",
            odata: ["gelijk aan", "niet gelijk aan", "kleiner dan", "kleiner dan of gelijk aan", "groter dan", "groter dan of gelijk aan", "begint met", "begint niet met", "is in", "is niet in", "eindigd met", "eindigd niet met", "bevat", "bevat niet"],
            groupOps: [{ op: "AND", text: "alle" }, { op: "OR", text: "een van de"}],
            matchText: " match",
            rulesText: " regels"
        },
        edit:
        {
            addCaption: "Nieuw",
            editCaption: "Bewerken",
            bSubmit: "Opslaan",
            bCancel: "Annuleren",
            bClose: "Sluiten",
            saveData: "Er is data aangepast! Wijzigingen opslaan?",
            bYes: "Ja",
            bNo: "Nee",
            bExit: "Sluiten",
            msg:
            {
                required: "Veld is verplicht",
                number: "Voer a.u.b. geldig nummer in",
                minValue: "Waarde moet groter of gelijk zijn aan ",
                maxValue: "Waarde moet kleiner of gelijks zijn aan",
                email: "is geen geldig e-mailadres",
                integer: "Voer a.u.b. een geldig getal in",
                date: "Voer a.u.b. een geldige waarde in",
                url: "is geen geldige URL. Prefix is verplicht ('http://' or 'https://')",
                nodefined : " is not defined!",
                novalue : " return value is required!",
                customarray : "Custom function should return array!",
                customfcheck : "Custom function should be present in case of custom checking!"
            }
        },
        view:
        {
            caption: "Tonen",
            bClose: "Sluiten"
        },
        del:
        {
            caption: "Verwijderen",
            msg: "Verwijder geselecteerde regel(s)?",
            bSubmit: "Verwijderen",
            bCancel: "Annuleren"
        },
        nav:
        {
            edittext: "",
            edittitle: "Bewerken",
            addtext: "",
            addtitle: "Nieuw",
            deltext: "",
            deltitle: "Verwijderen",
            searchtext: "",
            searchtitle: "Zoeken",
            refreshtext: "",
            refreshtitle: "Vernieuwen",
            alertcap: "Waarschuwing",
            alerttext: "Selecteer a.u.b. een regel",
            viewtext: "",
            viewtitle: "Openen"
        },
        col:
        {
            caption: "Tonen/verbergen kolommen",
            bSubmit: "OK",
            bCancel: "Annuleren"
        },
        errors:
        {
            errcap: "Fout",
            nourl: "Er is geen URL gedefinieerd",
            norecords: "Geen data om te verwerken",
            model: "Lengte van 'colNames' is niet gelijk aan 'colModel'!"
        },
        formatter:
        {
            integer:
            {
                thousandsSeparator: ".",
                defaultValue: "0"
            },
            number:
            {
                decimalSeparator: ",",
                thousandsSeparator: ".",
                decimalPlaces: 2,
                defaultValue: "0.00"
            },
            currency:
            {
                decimalSeparator: ",",
                thousandsSeparator: ".",
                decimalPlaces: 2,
                prefix: "EUR ",
                suffix: "",
                defaultValue: "0.00"
            },
            date:
            {
                dayNames: ["Zo", "Ma", "Di", "Wo", "Do", "Vr", "Za", "Zondag", "Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag"],
                monthNames: ["Jan", "Feb", "Maa", "Apr", "Mei", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Januari", "Februari", "Maart", "April", "Mei", "Juni", "Juli", "Augustus", "September", "October", "November", "December"],
                AmPm: ["am", "pm", "AM", "PM"],
                S: function(b) {
                    return b < 11 || b > 13 ? ["st", "nd", "rd", "th"][Math.min((b - 1) % 10, 3)] : "th"
                },
                srcformat: "Y-m-d",
                newformat: "d/m/Y",
                masks:
                {
                    ISO8601Long: "Y-m-d H:i:s",
                    ISO8601Short: "Y-m-d",
                    ShortDate: "n/j/Y",
                    LongDate: "l, F d, Y",
                    FullDateTime: "l d F Y G:i:s",
                    MonthDay: "d F",
                    ShortTime: "G:i",
                    LongTime: "G:i:s",
                    SortableDateTime: "Y-m-d\\TH:i:s",
                    UniversalSortableDateTime: "Y-m-d H:i:sO",
                    YearMonth: "F, Y"
                },
                reformatAfterEdit: false
            },
            baseLinkUrl: "",
            showAction: "",
            target: "",
            checkbox:
            {
                disabled: true
            },
            idName: "id"
        }
    }
})(jQuery);