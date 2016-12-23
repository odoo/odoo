(function( factory ) {
	if ( typeof define === "function" && define.amd ) {
		define( ["jquery", "../jquery.validate"], factory );
	} else {
		factory( jQuery );
	}
}(function( $ ) {

/*
 * Localized default methods for the jQuery validation plugin.
 * Locale: FI
 */
$.extend($.validator.methods, {
	date: function(value, element) {
		return this.optional(element) || /^\d{1,2}\.\d{1,2}\.\d{4}$/.test(value);
	},
	number: function(value, element) {
		return this.optional(element) || /^-?(?:\d+)(?:,\d+)?$/.test(value);
	}
});

}));