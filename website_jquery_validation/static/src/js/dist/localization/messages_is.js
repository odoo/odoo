(function( factory ) {
	if ( typeof define === "function" && define.amd ) {
		define( ["jquery", "../jquery.validate"], factory );
	} else {
		factory( jQuery );
	}
}(function( $ ) {

/*
 * Translated default messages for the jQuery validation plugin.
 * Locale: IS (Icelandic; íslenska)
 */
$.extend($.validator.messages, {
	required: "Þessi reitur er nauðsynlegur.",
	remote: "Lagaðu þennan reit.",
	maxlength: $.validator.format("Sláðu inn mest {0} stafi."),
	minlength: $.validator.format("Sláðu inn minnst {0} stafi."),
	rangelength: $.validator.format("Sláðu inn minnst {0} og mest {1} stafi."),
	email: "Sláðu inn gilt netfang.",
	url: "Sláðu inn gilda vefslóð.",
	date: "Sláðu inn gilda dagsetningu.",
	number: "Sláðu inn tölu.",
	digits: "Sláðu inn tölustafi eingöngu.",
	equalTo: "Sláðu sama gildi inn aftur.",
	range: $.validator.format("Sláðu inn gildi milli {0} og {1}."),
	max: $.validator.format("Sláðu inn gildi sem er minna en eða jafnt og {0}."),
	min: $.validator.format("Sláðu inn gildi sem er stærra en eða jafnt og {0}."),
	creditcard: "Sláðu inn gilt greiðslukortanúmer."
});

}));