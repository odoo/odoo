;(function($){
/**
 * jqGrid Danish Translation
 * Aesiras A/S
 * http://www.aesiras.dk
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/
$.jgrid = {
	defaults : {
		recordtext: "Vis {0} - {1} of {2}",
	    emptyrecords: "Ingen linjer fundet",
		loadtext: "Henter...",
		pgtext : "Side {0} af {1}"
	},
	search : {
	    caption: "Søg...",
	    Find: "Find",
	    Reset: "Nulstil",
	    odata : ['lig', 'forskellige fra', 'mindre', 'mindre eller lig','større','større eller lig', 'begynder med','begynder ikke med','findes i','findes ikke i','ender med','ender ikke med','indeholder','indeholder ikke'],
	    groupOps: [	{ op: "AND", text: "all" },	{ op: "OR",  text: "any" }	],
		matchText: " lig",
		rulesText: " regler"
	},
	edit : {
	    addCaption: "Tilføj",
	    editCaption: "Ret",
	    bSubmit: "Send",
	    bCancel: "Annuller",
		bClose: "Luk",
		saveData: "Data er ændret. Gem data?",
		bYes : "Ja",
		bNo : "Nej",
		bExit : "Fortryd",
	    msg: {
	        required:"Felt er nødvendigt",
	        number:"Indtast venligst et validt tal",
	        minValue:"værdi skal være større end eller lig med",
	        maxValue:"værdi skal være mindre end eller lig med",
	        email: "er ikke en gyldig email",
	        integer: "Indtast venligst et gyldigt heltal",
			date: "Indtast venligst en gyldig datoværdi",
			url: "er ugyldig URL. Prefix mangler ('http://' or 'https://')",
			nodefined : " er ikke defineret!",
			novalue : " returværdi kræves!",
			customarray : "Custom function should return array!",
			customfcheck : "Custom function should be present in case of custom checking!"
		}
	},
	view : {
	    caption: "Vis linje",
	    bClose: "Luk"
	},
	del : {
	    caption: "Slet",
	    msg: "Slet valgte linje(r)?",
	    bSubmit: "Slet",
	    bCancel: "Fortryd"
	},
	nav : {
		edittext: " ",
	    edittitle: "Rediger valgte linje",
		addtext:" ",
	    addtitle: "Tilføj ny linje",
	    deltext: " ",
	    deltitle: "Slet valgte linje",
	    searchtext: " ",
	    searchtitle: "Find linjer",
	    refreshtext: "",
	    refreshtitle: "Indlæs igen",
	    alertcap: "Advarsel",
	    alerttext: "Vælg venligst linje",
		viewtext: "",
		viewtitle: "Vis valgte linje"
	},
	col : {
	    caption: "Vis/skjul kolonner",
	    bSubmit: "Opdatere",
	    bCancel: "Fortryd"
	},
	errors : {
		errcap : "Fejl",
		nourl : "Ingen url valgt",
		norecords: "Ingen linjer at behandle",
	    model : "colNames og colModel har ikke samme længde!"
	},
	formatter : {
		integer : {thousandsSeparator: " ", defaultValue: '0'},
		number : {decimalSeparator:",", thousandsSeparator: " ", decimalPlaces: 2, defaultValue: '0,00'},
		currency : {decimalSeparator:",", thousandsSeparator: " ", decimalPlaces: 2, prefix: "", suffix:"", defaultValue: '0,00'},
		date : {
			dayNames:   [
				"Søn", "Man", "Tir", "Ons", "Tor", "Fre", "Lør",
				"Søndag", "Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "Lørdag"
			],
			monthNames: [
				"Jan", "Feb", "Mar", "Apr", "Maj", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dec",
				"Januar", "Februar", "Marts", "April", "Maj", "Juni", "Juli", "August", "September", "Oktober", "November", "December"
			],
			AmPm : ["","","",""],
			S: function (j) {return '.'},
			srcformat: 'Y-m-d',
			newformat: 'd/m/Y',
			masks : {
	            ISO8601Long:"Y-m-d H:i:s",
	            ISO8601Short:"Y-m-d",
	            ShortDate: "j/n/Y",
	            LongDate: "l d. F Y",
	            FullDateTime: "l d F Y G:i:s",
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
// DA
})(jQuery);
