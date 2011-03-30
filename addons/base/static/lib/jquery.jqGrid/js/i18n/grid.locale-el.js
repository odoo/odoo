;(function($){
/**
 * jqGrid Greek (el) Translation
 * Alex Cicovic
 * http://www.alexcicovic.com
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/
$.jgrid = {
	defaults : {
		recordtext: "View {0} - {1} of {2}",
	    emptyrecords: "No records to view",
		loadtext: "Φόρτωση...",
		pgtext : "Page {0} of {1}"
	},
	search : {
	    caption: "Αναζήτηση...",
	    Find: "Εύρεση",
	    Reset: "Επαναφορά",
	    odata : ['equal', 'not equal', 'less', 'less or equal','greater','greater or equal', 'begins with','does not begin with','is in','is not in','ends with','does not end with','contains','does not contain'],
	    groupOps: [	{ op: "AND", text: "all" },	{ op: "OR",  text: "any" }	],
		matchText: " match",
		rulesText: " rules"
	},
	edit : {
	    addCaption: "Εισαγωγή Εγγραφής",
	    editCaption: "Επεξεργασία Εγγραφής",
	    bSubmit: "Καταχώρηση",
	    bCancel: "Άκυρο",
		bClose: "Κλείσιμο",
		saveData: "Data has been changed! Save changes?",
		bYes : "Yes",
		bNo : "No",
		bExit : "Cancel",
	    msg: {
	        required:"Το πεδίο είναι απαραίτητο",
	        number:"Το πεδίο δέχεται μόνο αριθμούς",
	        minValue:"Η τιμή πρέπει να είναι μεγαλύτερη ή ίση του ",
	        maxValue:"Η τιμή πρέπει να είναι μικρότερη ή ίση του ",
	        email: "Η διεύθυνση e-mail δεν είναι έγκυρη",
	        integer: "Το πεδίο δέχεται μόνο ακέραιους αριθμούς",
			url: "is not a valid URL. Prefix required ('http://' or 'https://')",
			nodefined : " is not defined!",
			novalue : " return value is required!",
			customarray : "Custom function should return array!",
			customfcheck : "Custom function should be present in case of custom checking!"
		}
	},
	view : {
	    caption: "View Record",
	    bClose: "Close"
	},
	del : {
	    caption: "Διαγραφή",
	    msg: "Διαγραφή των επιλεγμένων εγγραφών;",
	    bSubmit: "Ναι",
	    bCancel: "Άκυρο"
	},
	nav : {
		edittext: " ",
	    edittitle: "Επεξεργασία επιλεγμένης εγγραφής",
		addtext:" ",
	    addtitle: "Εισαγωγή νέας εγγραφής",
	    deltext: " ",
	    deltitle: "Διαγραφή επιλεγμένης εγγραφής",
	    searchtext: " ",
	    searchtitle: "Εύρεση Εγγραφών",
	    refreshtext: "",
	    refreshtitle: "Ανανέωση Πίνακα",
	    alertcap: "Προσοχή",
	    alerttext: "Δεν έχετε επιλέξει εγγραφή",
		viewtext: "",
		viewtitle: "View selected row"
	},
	col : {
	    caption: "Εμφάνιση / Απόκρυψη Στηλών",
	    bSubmit: "ΟΚ",
	    bCancel: "Άκυρο"
	},
	errors : {
		errcap : "Σφάλμα",
		nourl : "Δεν έχει δοθεί διεύθυνση χειρισμού για τη συγκεκριμένη ενέργεια",
		norecords: "Δεν υπάρχουν εγγραφές προς επεξεργασία",
		model : "Άνισος αριθμός πεδίων colNames/colModel!"
	},
	formatter : {
		integer : {thousandsSeparator: " ", defaultValue: '0'},
		number : {decimalSeparator:".", thousandsSeparator: " ", decimalPlaces: 2, defaultValue: '0.00'},
		currency : {decimalSeparator:".", thousandsSeparator: " ", decimalPlaces: 2, prefix: "", suffix:"", defaultValue: '0.00'},
		date : {
			dayNames:   [
				"Κυρ", "Δευ", "Τρι", "Τετ", "Πεμ", "Παρ", "Σαβ",
				"Κυριακή", "Δευτέρα", "Τρίτη", "Τετάρτη", "Πέμπτη", "Παρασκευή", "Σάββατο"
			],
			monthNames: [
				"Ιαν", "Φεβ", "Μαρ", "Απρ", "Μαι", "Ιουν", "Ιουλ", "Αυγ", "Σεπ", "Οκτ", "Νοε", "Δεκ",
				"Ιανουάριος", "Φεβρουάριος", "Μάρτιος", "Απρίλιος", "Μάιος", "Ιούνιος", "Ιούλιος", "Αύγουστος", "Σεπτέμβριος", "Οκτώβριος", "Νοέμβριος", "Δεκέμβριος"
			],
			AmPm : ["πμ","μμ","ΠΜ","ΜΜ"],
			S: function (j) {return j == 1 || j > 1 ? ['η'][Math.min((j - 1) % 10, 3)] : ''},
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
