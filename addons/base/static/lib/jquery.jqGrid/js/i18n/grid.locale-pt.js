;(function($){
/**
 * jqGrid Portuguese Translation
* Tradução da jqGrid em Portugues por Frederico Carvalho, http://www.eyeviewdesign.pt
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/
$.jgrid = {
	defaults : {
		recordtext: "View {0} - {1} of {2}",
	    emptyrecords: "No records to view",
		loadtext: "A carregar...",
		pgtext : "Page {0} of {1}"
	},
	search : {
	    caption: "Busca...",
	    Find: "Procurar",
	    Reset: "Limpar",
	    odata : ['equal', 'not equal', 'less', 'less or equal','greater','greater or equal', 'begins with','does not begin with','is in','is not in','ends with','does not end with','contains','does not contain'],
	    groupOps: [	{ op: "AND", text: "all" },	{ op: "OR",  text: "any" }	],
		matchText: " match",
		rulesText: " rules"
	},
	edit : {
	    addCaption: "Adicionar Registo",
	    editCaption: "Modificar Registo",
	    bSubmit: "Submeter",
	    bCancel: "Cancelar",
		bClose: "Fechar",
		saveData: "Data has been changed! Save changes?",
		bYes : "Yes",
		bNo : "No",
		bExit : "Cancel",
	    msg: {
	        required:"Campo obrigatório",
	        number:"Por favor, introduza um numero",
	        minValue:"O valor deve ser maior ou igual que",
	        maxValue:"O valor deve ser menor ou igual a",
	        email: "Não é um endereço de email válido",
	        integer: "Por favor, introduza um numero inteiro",
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
	    caption: "Eliminar",
	    msg: "Deseja eliminar o(s) registo(s) seleccionado(s)?",
	    bSubmit: "Eliminar",
	    bCancel: "Cancelar"
	},
	nav : {
		edittext: " ",
	    edittitle: "Modificar registo seleccionado",
		addtext:" ",
	    addtitle: "Adicionar novo registo",
	    deltext: " ",
	    deltitle: "Eliminar registo seleccionado",
	    searchtext: " ",
	    searchtitle: "Procurar",
	    refreshtext: "",
	    refreshtitle: "Actualizar",
	    alertcap: "Aviso",
	    alerttext: "Por favor, seleccione um registo",
		viewtext: "",
		viewtitle: "View selected row"
	},
	col : {
	    caption: "Mostrar/Ocultar Colunas",
	    bSubmit: "Enviar",
	    bCancel: "Cancelar"	
	},
	errors : {
		errcap : "Erro",
		nourl : "Não especificou um url",
		norecords: "Não existem dados para processar",
	    model : "Tamanho do colNames <> colModel!"
	},
	formatter : {
		integer : {thousandsSeparator: " ", defaultValue: '0'},
		number : {decimalSeparator:".", thousandsSeparator: " ", decimalPlaces: 2, defaultValue: '0.00'},
		currency : {decimalSeparator:".", thousandsSeparator: " ", decimalPlaces: 2, prefix: "", suffix:"", defaultValue: '0.00'},
		date : {
			dayNames:   [
				"Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sab",
				"Domingo", "Segunda-Feira", "Terça-Feira", "Quarta-Feira", "Quinta-Feira", "Sexta-Feira", "Sábado"
			],
			monthNames: [
				"Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez",
				"Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
			],
			AmPm : ["am","pm","AM","PM"],
			S: function (j) {return j < 11 || j > 13 ? ['º', 'º', 'º', 'º'][Math.min((j - 1) % 10, 3)] : 'º'},
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
