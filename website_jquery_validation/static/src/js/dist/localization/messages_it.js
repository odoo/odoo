(function( factory ) {
	if ( typeof define === "function" && define.amd ) {
		define( ["jquery", "../jquery.validate"], factory );
	} else {
		factory( jQuery );
	}
}(function( $ ) {

/*
 * Translated default messages for the jQuery validation plugin.
 * Locale: IT (Italian; Italiano)
 */
$.extend($.validator.messages, {
	required: "Campo obbligatorio",
	remote: "Controlla questo campo",
	email: "Inserisci un indirizzo email valido",
	url: "Inserisci un indirizzo web valido",
	date: "Inserisci una data valida",
	dateISO: "Inserisci una data valida (ISO)",
	number: "Inserisci un numero valido",
	digits: "Inserisci solo numeri",
	creditcard: "Inserisci un numero di carta di credito valido",
	equalTo: "Il valore non corrisponde",
	extension: "Inserisci un valore con un&apos;estensione valida",
	maxlength: $.validator.format("Non inserire pi&ugrave; di {0} caratteri"),
	minlength: $.validator.format("Inserisci almeno {0} caratteri"),
	rangelength: $.validator.format("Inserisci un valore compreso tra {0} e {1} caratteri"),
	range: $.validator.format("Inserisci un valore compreso tra {0} e {1}"),
	max: $.validator.format("Inserisci un valore minore o uguale a {0}"),
	min: $.validator.format("Inserisci un valore maggiore o uguale a {0}"),
	nifES: "Inserisci un NIF valido",
	nieES: "Inserisci un NIE valido",
	cifES: "Inserisci un CIF valido",
	currency: "Inserisci una valuta valida"
});

}));