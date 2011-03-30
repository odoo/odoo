;(function($){
/**
 * jqGrid Swedish Translation
 * Harald Normann harald.normann@wts.se, harald.normann@gmail.com
 * http://www.worldteamsoftware.com 
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/
$.jgrid = {
	defaults : {
		recordtext: "Visar {0} - {1} av {2}",
		emptyrecords: "Det finns inga poster att visa",
		loadtext: "Laddar...",
		pgtext : "Sida {0} av {1}"
	},
	search : {
		caption: "Sök Poster - Ange sökvillkor",
		Find: "Sök",
		Reset: "Nollställ Villkor",
		odata : ['lika', 'ej lika', 'mindre', 'mindre eller lika','större','större eller lika', 'börjar med','börjar inte med','tillhör','tillhör inte','slutar med','slutar inte med','innehåller','innehåller inte'],
		groupOps: [	{ op: "AND", text: "alla" },	{ op: "OR",  text: "eller" }	],
		matchText: " träff",
		rulesText: " regler"
	},
	edit : {
		addCaption: "Ny Post",
		editCaption: "Redigera Post",
		bSubmit: "Spara",
		bCancel: "Avbryt",
		bClose: "Stäng",
		saveData: "Data har ändrats! Spara förändringar?",
		bYes : "Ja",
		bNo : "Nej",
		bExit : "Avbryt",
		msg: {
	        required:"Fältet är obligatoriskt",
	        number:"Välj korrekt nummer",
	        minValue:"värdet måste vara större än eller lika med",
	        maxValue:"värdet måste vara mindre än eller lika med",
	        email: "är inte korrekt e-post adress",
	        integer: "Var god ange korrekt heltal",
	        date: "Var god ange korrekt datum",
	        url: "är inte en korrekt URL. Prefix måste anges ('http://' or 'https://')",
	        nodefined : " är inte definierad!",
	        novalue : " returvärde måste anges!",
	        customarray : "Custom funktion måste returnera en vektor!",
			customfcheck : "Custom funktion måste finnas om Custom kontroll sker!"
		}
	},
	view : {
		caption: "Visa Post",
		bClose: "Stäng"
	},
	del : {
		caption: "Radera",
		msg: "Radera markerad(e) post(er)?",
		bSubmit: "Radera",
		bCancel: "Avbryt"
	},
	nav : {
		edittext: "",
		edittitle: "Redigera markerad rad",
		addtext:"",
		addtitle: "Skapa ny post",
		deltext: "",
		deltitle: "Radera markerad rad",
		searchtext: "",
		searchtitle: "Sök poster",
		refreshtext: "",
		refreshtitle: "Uppdatera data",
		alertcap: "Varning",
		alerttext: "Ingen rad är markerad",
		viewtext: "",
		viewtitle: "Visa markerad rad"
	},
	col : {
		caption: "Välj Kolumner",
		bSubmit: "OK",
		bCancel: "Avbryt"
	},
	errors : {
		errcap : "Fel",
		nourl : "URL saknas",
		norecords: "Det finns inga poster att bearbeta",
		model : "Antal colNames <> colModel!"
	},
	formatter : {
		integer : {thousandsSeparator: " ", defaultValue: '0'},
		number : {decimalSeparator:",", thousandsSeparator: " ", decimalPlaces: 2, defaultValue: '0,00'},
		currency : {decimalSeparator:",", thousandsSeparator: " ", decimalPlaces: 2, prefix: "", suffix:"Kr", defaultValue: '0,00'},
		date : {
			dayNames:   [
				"Sön", "Mån", "Tis", "Ons", "Tor", "Fre", "Lör",
				"Söndag", "Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag"
			],
			monthNames: [
				"Jan", "Feb", "Mar", "Apr", "Maj", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dec",
				"Januari", "Februari", "Mars", "April", "Maj", "Juni", "Juli", "Augusti", "September", "Oktober", "November", "December"
			],
			AmPm : ["fm","em","FM","EM"],
			S: function (j) {return j < 11 || j > 13 ? ['st', 'nd', 'rd', 'th'][Math.min((j - 1) % 10, 3)] : 'th'},
			srcformat: 'Y-m-d',
			newformat: 'Y-m-d',
			masks : {
	            ISO8601Long:"Y-m-d H:i:s",
	            ISO8601Short:"Y-m-d",
	            ShortDate:  "n/j/Y",
	            LongDate: "l, F d, Y",
	            FullDateTime: "l, F d, Y g:i:s A",
	            MonthDay: "F d",
	            ShortTime: "g:i A",
	            LongTime: "g:i:s A",
	            SortableDateTime: "Y-m-d\\TH:i:s",
	            UniversalSortableDateTime: "Y-m-d H:i:sO",
	            YearMonth: "F, Y"
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
