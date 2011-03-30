;(function($){
/**
 * jqGrid Slovak Translation
 * Milan Cibulka
 * http://trirand.com/blog/ 
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/
$.jgrid = {
	defaults : {
		recordtext: "Zobrazených {0} - {1} z {2} záznamov",
	    emptyrecords: "Neboli nájdené žiadne záznamy",
		loadtext: "Načítám...",
		pgtext : "Strana {0} z {1}"
	},
	search : {
		caption: "Vyhľadávam...",
		Find: "Hľadať",
		Reset: "Reset",
	    odata : ['rovná sa', 'nerovná sa', 'menšie', 'menšie alebo rovnajúce sa','väčšie', 'väčšie alebo rovnajúce sa', 'začína s', 'nezačína s', 'je v', 'nie je v', 'končí s', 'nekončí s', 'obahuje', 'neobsahuje'],
	    groupOps: [	{ op: "AND", text: "všetkých" },	{ op: "OR",  text: "niektorého z" }	],
		matchText: " hľadať podla",
		rulesText: " pravidiel"
	},
	edit : {
		addCaption: "Pridať záznam",
		editCaption: "Editácia záznamov",
		bSubmit: "Uložiť",
		bCancel: "Storno",
		bClose: "Zavrieť",
		saveData: "Údaje boli zmenené! Uložiť zmeny?",
		bYes : "Ano",
		bNo : "Nie",
		bExit : "Zrušiť",
		msg: {
		    required:"Pole je požadované",
		    number:"Prosím, vložte valídne číslo",
		    minValue:"hodnota musí býť väčšia ako alebo rovná ",
		    maxValue:"hodnota musí býť menšia ako alebo rovná ",
		    email: "nie je valídny e-mail",
		    integer: "Prosím, vložte celé číslo",
			date: "Prosím, vložte valídny dátum",
			url: "nie je platnou URL. Požadovaný prefix ('http://' alebo 'https://')",
			nodefined : " nie je definovaný!",
			novalue : " je vyžadovaná návratová hodnota!",
			customarray : "Custom function mala vrátiť pole!",
			customfcheck : "Custom function by mala byť prítomná v prípade custom checking!"
		}
	},
	view : {
	    caption: "Zobraziť záznam",
	    bClose: "Zavrieť"
	},
	del : {
		caption: "Zmazať",
		msg: "Zmazať vybraný(é) záznam(y)?",
		bSubmit: "Zmazať",
		bCancel: "Storno"
	},
	nav : {
		edittext: " ",
		edittitle: "Editovať vybraný riadok",
		addtext:" ",
		addtitle: "Pridať nový riadek",
		deltext: " ",
		deltitle: "Zmazať vybraný záznam ",
		searchtext: " ",
		searchtitle: "Nájsť záznamy",
		refreshtext: "",
		refreshtitle: "Obnoviť tabuľku",
		alertcap: "Varovanie",
		alerttext: "Prosím, vyberte riadok",
		viewtext: "",
		viewtitle: "Zobraziť vybraný riadok"
	},
	col : {
		caption: "Zobrazit/Skrýť stĺpce",
		bSubmit: "Uložiť",
		bCancel: "Storno"	
	},
	errors : {
		errcap : "Chyba",
		nourl : "Nie je nastavená url",
		norecords: "Žiadne záznamy k spracovaniu",
		model : "Dĺžka colNames <> colModel!"
	},
	formatter : {
		integer : {thousandsSeparator: " ", defaultValue: '0'},
		number : {decimalSeparator:".", thousandsSeparator: " ", decimalPlaces: 2, defaultValue: '0.00'},
		currency : {decimalSeparator:".", thousandsSeparator: " ", decimalPlaces: 2, prefix: "", suffix:"", defaultValue: '0.00'},
		date : {
			dayNames:   [
				"Ne", "Po", "Ut", "St", "Št", "Pi", "So",
				"Nedela", "Pondelok", "Utorok", "Streda", "Štvrtok", "Piatek", "Sobota"
			],
			monthNames: [
				"Jan", "Feb", "Mar", "Apr", "Máj", "Jún", "Júl", "Aug", "Sep", "Okt", "Nov", "Dec",
				"Január", "Február", "Marec", "Apríl", "Máj", "Jún", "Júl", "August", "September", "Október", "November", "December"
			],
			AmPm : ["do","od","DO","OD"],
			S: function (j) {return j < 11 || j > 13 ? ['st', 'nd', 'rd', 'th'][Math.min((j - 1) % 10, 3)] : 'th'},
			srcformat: 'Y-m-d',
			newformat: 'd/m/Y',
			masks : {
		        ISO8601Long:"Y-m-d H:i:s",
		        ISO8601Short:"Y-m-d",
		        ShortDate: "n/j/Y",
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
