;(function($){
/**
 * jqGrid Czech Translation
 * Pavel Jirak pavel.jirak@jipas.cz
 * doplnil Thomas Wagner xwagne01@stud.fit.vutbr.cz
 * http://trirand.com/blog/ 
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/
$.jgrid = {
	defaults : {
		recordtext: "Zobrazeno {0} - {1} z {2} záznamů",
	    emptyrecords: "Nenalezeny žádné záznamy",
		loadtext: "Načítám...",
		pgtext : "Strana {0} z {1}"
	},
	search : {
		caption: "Vyhledávám...",
		Find: "Hledat",
		Reset: "Reset",
	    odata : ['rovno', 'nerovono', 'menší', 'menší nebo rovno','větší', 'větší nebo rovno', 'začíná s', 'nezačíná s', 'je v', 'není v', 'končí s', 'nekončí s', 'obahuje', 'neobsahuje'],
	    groupOps: [	{ op: "AND", text: "všech" },	{ op: "OR",  text: "některého z" }	],
		matchText: " hledat podle",
		rulesText: " pravidel"
	},
	edit : {
		addCaption: "Přidat záznam",
		editCaption: "Editace záznamu",
		bSubmit: "Uložit",
		bCancel: "Storno",
		bClose: "Zavřít",
		saveData: "Data byla změněna! Uložit změny?",
		bYes : "Ano",
		bNo : "Ne",
		bExit : "Zrušit",
		msg: {
		    required:"Pole je vyžadováno",
		    number:"Prosím, vložte validní číslo",
		    minValue:"hodnota musí být větší než nebo rovná ",
		    maxValue:"hodnota musí být menší než nebo rovná ",
		    email: "není validní e-mail",
		    integer: "Prosím, vložte celé číslo",
			date: "Prosím, vložte validní datum",
			url: "není platnou URL. Vyžadován prefix ('http://' or 'https://')",
			nodefined : " není definován!",
			novalue : " je vyžadována návratová hodnota!",
			customarray : "Custom function mělá vrátit pole!",
			customfcheck : "Custom function by měla být přítomna v případě custom checking!"
		}
	},
	view : {
	    caption: "Zobrazit záznam",
	    bClose: "Zavřít"
	},
	del : {
		caption: "Smazat",
		msg: "Smazat vybraný(é) záznam(y)?",
		bSubmit: "Smazat",
		bCancel: "Storno"
	},
	nav : {
		edittext: " ",
		edittitle: "Editovat vybraný řádek",
		addtext:" ",
		addtitle: "Přidat nový řádek",
		deltext: " ",
		deltitle: "Smazat vybraný záznam ",
		searchtext: " ",
		searchtitle: "Najít záznamy",
		refreshtext: "",
		refreshtitle: "Obnovit tabulku",
		alertcap: "Varování",
		alerttext: "Prosím, vyberte řádek",
		viewtext: "",
		viewtitle: "Zobrazit vybraný řádek"
	},
	col : {
		caption: "Zobrazit/Skrýt sloupce",
		bSubmit: "Uložit",
		bCancel: "Storno"	
	},
	errors : {
		errcap : "Chyba",
		nourl : "Není nastavena url",
		norecords: "Žádné záznamy ke zpracování",
		model : "Délka colNames <> colModel!"
	},
	formatter : {
		integer : {thousandsSeparator: " ", defaultValue: '0'},
		number : {decimalSeparator:".", thousandsSeparator: " ", decimalPlaces: 2, defaultValue: '0.00'},
		currency : {decimalSeparator:".", thousandsSeparator: " ", decimalPlaces: 2, prefix: "", suffix:"", defaultValue: '0.00'},
		date : {
			dayNames:   [
				"Ne", "Po", "Út", "St", "Čt", "Pá", "So",
				"Neděle", "Pondělí", "Úterý", "Středa", "Čtvrtek", "Pátek", "Sobota"
			],
			monthNames: [
				"Led", "Úno", "Bře", "Dub", "Kvě", "Čer", "Čvc", "Srp", "Zář", "Říj", "Lis", "Pro",
				"Leden", "Únor", "Březen", "Duben", "Květen", "Červen", "Červenec", "Srpen", "Září", "Říjen", "Listopad", "Prosinec"
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
