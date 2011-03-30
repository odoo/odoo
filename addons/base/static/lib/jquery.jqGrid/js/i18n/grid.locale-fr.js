;(function($){
/**
 * jqGrid French Translation
 * Tony Tomov tony@trirand.com
 * http://trirand.com/blog/ 
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/
$.jgrid = {
	defaults : {
		recordtext: "Enregistrements {0} - {1} sur {2}",
		emptyrecords: "Aucun enregistrement à afficher",
		loadtext: "Chargement...",
		pgtext : "Page {0} sur {1}"
	},
	search : {
		caption: "Recherche...",
		Find: "Chercher",
		Reset: "Annuler",
		odata : ['égal', 'différent', 'inférieur', 'inférieur ou égal','supérieur','supérieur ou égal', 'commence par','ne commence pas par','est dans',"n'est pas dans",'finit par','ne finit pas par','contient','ne contient pas'],
		groupOps: [	{ op: "AND", text: "tous" },	{ op: "OR",  text: "aucun" }	],
		matchText: " correspondance",
		rulesText: " règles"
	},
	edit : {
		addCaption: "Ajouter",
		editCaption: "Editer",
		bSubmit: "Valider",
		bCancel: "Annuler",
		bClose: "Fermer",
		saveData: "Les données ont changé ! Enregistrer les modifications ?",
		bYes: "Oui",
		bNo: "Non",
		bExit: "Annuler",
		msg: {
			required: "Champ obligatoire",
			number: "Saisissez un nombre correct",
			minValue: "La valeur doit être supérieure ou égale à",
			maxValue: "La valeur doit être inférieure ou égale à",
			email: "n'est pas un email correct",
			integer: "Saisissez un entier correct",
			url: "n'est pas une adresse correcte. Préfixe requis ('http://' or 'https://')",
			nodefined : " n'est pas défini!",
			novalue : " la valeur de retour est requise!",
			customarray : "Une fonction personnalisée devrait retourner un tableau (array)!",
			customfcheck : "Une fonction personnalisée devrait être présente dans le cas d'une vérification personnalisée!"
		}
	},
	view : {
		caption: "Voir les enregistrement",
		bClose: "Fermer"
	},
	del : {
		caption: "Supprimer",
		msg: "Supprimer les enregistrements sélectionnés ?",
		bSubmit: "Supprimer",
		bCancel: "Annuler"
	},
	nav : {
		edittext: " ",
		edittitle: "Editer la ligne sélectionnée",
		addtext:" ",
		addtitle: "Ajouter une ligne",
		deltext: " ",
		deltitle: "Supprimer la ligne sélectionnée",
		searchtext: " ",
		searchtitle: "Chercher un enregistrement",
		refreshtext: "",
		refreshtitle: "Recharger le tableau",
		alertcap: "Avertissement",
		alerttext: "Veuillez sélectionner une ligne",
		viewtext: "",
		viewtitle: "Afficher la ligne sélectionnée"
	},
	col : {
		caption: "Afficher/Masquer les colonnes",
		bSubmit: "Valider",
		bCancel: "Annuler"
	},
	errors : {
		errcap : "Erreur",
		nourl : "Aucune adresse n'est paramétrée",
		norecords: "Aucun enregistrement à traiter",
		model : "Nombre de titres (colNames) <> Nombre de données (colModel)!"
	},
	formatter : {
		integer : {thousandsSeparator: " ", defaultValue: '0'},
		number : {decimalSeparator:",", thousandsSeparator: " ", decimalPlaces: 2, defaultValue: '0,00'},
		currency : {decimalSeparator:",", thousandsSeparator: " ", decimalPlaces: 2, prefix: "", suffix:"", defaultValue: '0,00'},
		date : {
			dayNames:   [
				"Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam",
				"Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"
			],
			monthNames: [
				"Jan", "Fév", "Mar", "Avr", "Mai", "Jui", "Jul", "Aou", "Sep", "Oct", "Nov", "Déc",
				"Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Aout", "Septembre", "Octobre", "Novembre", "Décembre"
			],
			AmPm : ["am","pm","AM","PM"],
			S: function (j) {return j == 1 ? 'er' : 'e';},
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
