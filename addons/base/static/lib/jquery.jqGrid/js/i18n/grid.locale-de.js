;(function($){
/**
 * jqGrid German Translation
 * Version 1.0.0 (developed for jQuery Grid 3.3.1)
 * Olaf Klöppel opensource@blue-hit.de
 * http://blue-hit.de/ 
 *
 * Updated for jqGrid 3.8
 * Andreas Flack
 * http://www.contentcontrol-berlin.de
 *
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/
$.jgrid = {
	defaults : {
		recordtext: "Zeige {0} - {1} von {2}",
	    emptyrecords: "Keine Datensätze vorhanden",
		loadtext: "Lädt...",
		pgtext : "Seite {0} von {1}"
	},
	search : {
		caption: "Suche...",
		Find: "Suchen",
		Reset: "Zurücksetzen",
	    odata : ['gleich', 'ungleich', 'kleiner', 'kleiner gleich','größer','größer gleich', 'beginnt mit','beginnt nicht mit','ist in','ist nicht in','endet mit','endet nicht mit','enthält','enthält nicht'],
	    groupOps: [	{ op: "AND", text: "alle" },	{ op: "OR",  text: "mindestens eine" }	],
		matchText: " erfülle",
		rulesText: " Bedingung(en)"
	},
	edit : {
		addCaption: "Datensatz hinzufügen",
		editCaption: "Datensatz bearbeiten",
		bSubmit: "Speichern",
		bCancel: "Abbrechen",
		bClose: "Schließen",
		saveData: "Daten wurden geändert! Änderungen speichern?",
		bYes : "ja",
		bNo : "nein",
		bExit : "abbrechen",
		msg: {
		    required:"Feld ist erforderlich",
		    number: "Bitte geben Sie eine Zahl ein",
		    minValue:"Wert muss größer oder gleich sein, als ",
		    maxValue:"Wert muss kleiner oder gleich sein, als ",
		    email: "ist keine gültige E-Mail-Adresse",
		    integer: "Bitte geben Sie eine Ganzzahl ein",
			date: "Bitte geben Sie ein gültiges Datum ein",
			url: "ist keine gültige URL. Präfix muss eingegeben werden ('http://' oder 'https://')",
			nodefined : " ist nicht definiert!",
			novalue : " Rückgabewert ist erforderlich!",
			customarray : "Benutzerdefinierte Funktion sollte ein Array zurückgeben!",
			customfcheck : "Benutzerdefinierte Funktion sollte im Falle der benutzerdefinierten Überprüfung vorhanden sein!"
		}
	},
	view : {
	    caption: "Datensatz anzeigen",
	    bClose: "Schließen"
	},
	del : {
		caption: "Löschen",
		msg: "Ausgewählte Datensätze löschen?",
		bSubmit: "Löschen",
		bCancel: "Abbrechen"
	},
	nav : {
		edittext: " ",
	    edittitle: "Ausgewählte Zeile editieren",
		addtext:" ",
	    addtitle: "Neue Zeile einfügen",
	    deltext: " ",
	    deltitle: "Ausgewählte Zeile löschen",
	    searchtext: " ",
	    searchtitle: "Datensatz suchen",
	    refreshtext: "",
	    refreshtitle: "Tabelle neu laden",
	    alertcap: "Warnung",
	    alerttext: "Bitte Zeile auswählen",
		viewtext: "",
		viewtitle: "Ausgewählte Zeile anzeigen"
	},
	col : {
		caption: "Spalten auswählen",
		bSubmit: "Speichern",
		bCancel: "Abbrechen"	
	},
	errors : {
		errcap : "Fehler",
		nourl : "Keine URL angegeben",
		norecords: "Keine Datensätze zu bearbeiten",
		model : "colNames und colModel sind unterschiedlich lang!"
	},
	formatter : {
		integer : {thousandsSeparator: ".", defaultValue: '0'},
		number : {decimalSeparator:",", thousandsSeparator: ".", decimalPlaces: 2, defaultValue: '0,00'},
		currency : {decimalSeparator:",", thousandsSeparator: ".", decimalPlaces: 2, prefix: "", suffix:" €", defaultValue: '0,00'},
		date : {
			dayNames:   [
				"So", "Mo", "Di", "Mi", "Do", "Fr", "Sa",
				"Sonntag", "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag"
			],
			monthNames: [
				"Jan", "Feb", "Mar", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez",
				"Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"
			],
			AmPm : ["am","pm","AM","PM"],
			S: function (j) {return 'ter'},
			srcformat: 'Y-m-d',
			newformat: 'd.m.Y',
			masks : {
		        ISO8601Long: "Y-m-d H:i:s",
		        ISO8601Short: "Y-m-d",
		        ShortDate: "j.n.Y",
		        LongDate: "l, j. F Y",
		        FullDateTime: "l, d. F Y G:i:s",
		        MonthDay: "d. F",
		        ShortTime: "G:i",
		        LongTime: "G:i:s",
		        SortableDateTime: "Y-m-d\\TH:i:s",
		        UniversalSortableDateTime: "Y-m-d H:i:sO",
		        YearMonth: "F Y"
		    },
		    reformatAfterEdit : false
		},
		baseLinkUrl: '',
		showAction: '',
	    target: '',
	    checkbox : {disabled:true},
		idName : 'id'
	}
};
})(jQuery);