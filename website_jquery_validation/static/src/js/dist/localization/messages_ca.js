(function( factory ) {
	if ( typeof define === "function" && define.amd ) {
		define( ["jquery", "../jquery.validate"], factory );
	} else {
		factory( jQuery );
	}
}(function( $ ) {

/*
 * Translated default messages for the jQuery validation plugin.
 * Locale: CA (Catalan; català)
 */
$.extend($.validator.messages, {
	required: "Aquest camp és obligatori.",
	remote: "Si us plau, omple aquest camp.",
	email: "Si us plau, escriu una adreça de correu-e vàlida",
	url: "Si us plau, escriu una URL vàlida.",
	date: "Si us plau, escriu una data vàlida.",
	dateISO: "Si us plau, escriu una data (ISO) vàlida.",
	number: "Si us plau, escriu un número enter vàlid.",
	digits: "Si us plau, escriu només dígits.",
	creditcard: "Si us plau, escriu un número de tarjeta vàlid.",
	equalTo: "Si us plau, escriu el mateix valor de nou.",
	extension: "Si us plau, escriu un valor amb una extensió acceptada.",
	maxlength: $.validator.format("Si us plau, no escriguis més de {0} caracters."),
	minlength: $.validator.format("Si us plau, no escriguis menys de {0} caracters."),
	rangelength: $.validator.format("Si us plau, escriu un valor entre {0} i {1} caracters."),
	range: $.validator.format("Si us plau, escriu un valor entre {0} i {1}."),
	max: $.validator.format("Si us plau, escriu un valor menor o igual a {0}."),
	min: $.validator.format("Si us plau, escriu un valor major o igual a {0}.")
});

}));