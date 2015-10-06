(function( factory ) {
	if ( typeof define === "function" && define.amd ) {
		define( ["jquery", "../jquery.validate"], factory );
	} else {
		factory( jQuery );
	}
}(function( $ ) {

/*
 * Translated default messages for the jQuery validation plugin.
 * Locale: ET (Estonian; eesti, eesti keel)
 */
$.extend($.validator.messages, {
	required: "See väli peab olema täidetud.",
	maxlength: $.validator.format("Palun sisestage vähem kui {0} tähemärki."),
	minlength: $.validator.format("Palun sisestage vähemalt {0} tähemärki."),
	rangelength: $.validator.format("Palun sisestage väärtus vahemikus {0} kuni {1} tähemärki."),
	email: "Palun sisestage korrektne e-maili aadress.",
	url: "Palun sisestage korrektne URL.",
	date: "Palun sisestage korrektne kuupäev.",
	dateISO: "Palun sisestage korrektne kuupäev (YYYY-MM-DD).",
	number: "Palun sisestage korrektne number.",
	digits: "Palun sisestage ainult numbreid.",
	equalTo: "Palun sisestage sama väärtus uuesti.",
	range: $.validator.format("Palun sisestage väärtus vahemikus {0} kuni {1}."),
	max: $.validator.format("Palun sisestage väärtus, mis on väiksem või võrdne arvuga {0}."),
	min: $.validator.format("Palun sisestage väärtus, mis on suurem või võrdne arvuga {0}."),
	creditcard: "Palun sisestage korrektne krediitkaardi number."
});

}));