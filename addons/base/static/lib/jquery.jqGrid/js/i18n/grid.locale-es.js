;(function($){
/**
 * jqGrid Spanish Translation
 * Traduccion jqGrid en Español por Yamil Bracho
 * Traduccion corregida y ampliada por Faserline, S.L. 
 * http://www.faserline.com
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/
$.jgrid = {
	defaults : {
		recordtext: "Mostrando {0} - {1} de {2}",
	    emptyrecords: "Sin registros que mostrar",
		loadtext: "Cargando...",
		pgtext : "Página {0} de {1}"
	},
	search : {
	    caption: "Búsqueda...",
	    Find: "Buscar",
	    Reset: "Limpiar",
	    odata : ['igual ', 'no igual a', 'menor que', 'menor o igual que','mayor que','mayor o igual a', 'empiece por','no empiece por','está en','no está en','termina por','no termina por','contiene','no contiene'],
	    groupOps: [	{ op: "AND", text: "todo" },	{ op: "OR",  text: "cualquier" }	],
		matchText: " match",
		rulesText: " reglas"
	},
	edit : {
	    addCaption: "Agregar registro",
	    editCaption: "Modificar registro",
	    bSubmit: "Guardar",
	    bCancel: "Cancelar",
		bClose: "Cerrar",
		saveData: "Se han modificado los datos, ¿guardar cambios?",
		bYes : "Si",
		bNo : "No",
		bExit : "Cancelar",
	    msg: {
	        required:"Campo obligatorio",
	        number:"Introduzca un número",
	        minValue:"El valor debe ser mayor o igual a ",
	        maxValue:"El valor debe ser menor o igual a ",
	        email: "no es una dirección de correo válida",
	        integer: "Introduzca un valor entero",
			date: "Introduza una fecha correcta ",
			url: "no es una URL válida. Prefijo requerido ('http://' or 'https://')",
			nodefined : " no está definido.",
			novalue : " valor de retorno es requerido.",
			customarray : "La función personalizada debe devolver un array.",
			customfcheck : "La función personalizada debe estar presente en el caso de validación personalizada."
		}
	},
	view : {
	    caption: "Consultar registro",
	    bClose: "Cerrar"
	},
	del : {
	    caption: "Eliminar",
	    msg: "¿Desea eliminar los registros seleccionados?",
	    bSubmit: "Eliminar",
	    bCancel: "Cancelar"
	},
	nav : {
		edittext: " ",
	    edittitle: "Modificar fila seleccionada",
		addtext:" ",
	    addtitle: "Agregar nueva fila",
	    deltext: " ",
	    deltitle: "Eliminar fila seleccionada",
	    searchtext: " ",
	    searchtitle: "Buscar información",
	    refreshtext: "",
	    refreshtitle: "Recargar datos",
	    alertcap: "Aviso",
	    alerttext: "Seleccione una fila",
		viewtext: "",
		viewtitle: "Ver fila seleccionada"
	},
	col : {
	    caption: "Mostrar/ocultar columnas",
	    bSubmit: "Enviar",
	    bCancel: "Cancelar"	
	},
	errors : {
		errcap : "Error",
		nourl : "No se ha especificado una URL",
		norecords: "No hay datos para procesar",
	    model : "Las columnas de nombres son diferentes de las columnas de modelo"
	},
	formatter : {
		integer : {thousandsSeparator: ".", defaultValue: '0'},
		number : {decimalSeparator:",", thousandsSeparator: ".", decimalPlaces: 2, defaultValue: '0,00'},
		currency : {decimalSeparator:",", thousandsSeparator: ".", decimalPlaces: 2, prefix: "", suffix:"", defaultValue: '0,00'},
		date : {
			dayNames:   [
				"Do", "Lu", "Ma", "Mi", "Ju", "Vi", "Sa",
				"Domingo", "Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado"
			],
			monthNames: [
				"Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
				"Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
			],
			AmPm : ["am","pm","AM","PM"],
			S: function (j) {return j < 11 || j > 13 ? ['st', 'nd', 'rd', 'th'][Math.min((j - 1) % 10, 3)] : 'th'},
			srcformat: 'Y-m-d',
			newformat: 'd-m-Y',
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
