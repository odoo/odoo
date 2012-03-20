/* **************************************************************************************
   * BarcodeListener v 1.1 (jQuery plug-in)                                             *
   * http://code.google.com/p/jquery-barcodelistener/                                   *
   *                                                                                    *
   * how to setup the plugin http://code.google.com/p/jquery-barcodelistener/wiki/setup * 
   *                                                                                    *
   * made by Gregorio Pellegrino                                                        *
   *         gregoriopellegrino.com                                                     *
   *         mail@gregoriopellegrino.com                                                *
   *                                                                                    *
   * relased under Apache License 2.0 (http://www.apache.org/licenses/LICENSE-2.0)      *
   ************************************************************************************** */
   
(function($) {
	jQuery.fn.BarcodeListener = function(options, callback) {
					
		//inizializza le variabili
		char0 = new Array("§", "32");
		char1 = new Array("~", "732");
		settings = new Array(char0, char1);
		if(options) {
			jQuery.extend(settings,options);
		}
					
		// appende form nascosto
		$("body").append("<form id=\"29LLRUZk\" style=\"opacity:0;\"><input type=\"text\" name=\"L3ZitQdL\" id=\"L3ZitQdL\" /></form>");
					
		// intercetta barcode reader con sequenza di caratteri §~
		$(document).keypress(function(e) {
			if (e.which == settings[0][1]) {
				if(settings.length-1>0) {
					wlBUJTIw = 1;
					xaWi4Y4y = true;
					while ((wlBUJTIw < settings.length) && (xaWi4Y4y == true)) {
						$(document).keypress(function(e) {
							if (e.which == settings[wlBUJTIw][1]) {
								xaWi4Y4y = true;
							} else {
								xaWi4Y4y = false;	
							}
						});
						wlBUJTIw++;
					}
					if (xaWi4Y4y == true) {
						$("#L3ZitQdL").val("").focus();
					}
				} else {
					$("#L3ZitQdL").val("").focus();
				}
				
				// event propagation
                e.cancelBubble = true;
                e.returnValue = false;

                if (e.stopPropagation) {
                    e.stopPropagation();
                    e.preventDefault();
                } 
				
			}
		});
						
		// intercetta invio del form
		$("#29LLRUZk").submit(function() {
			code = $("#L3ZitQdL").val();
			for (i=0; i<settings.length; i++) {
				dUWThqjL = new RegExp(settings[i][0]);
				code = code.replace(dUWThqjL, "");
			}

			//restituisce funzione con valore immesso
			if (typeof(callback) == "function") {
				callback(code);
			}
						
			return false;
		});
	}
})(jQuery);