/* http://keith-wood.name/realPerson.html
   Real Person Form Submission for jQuery v1.1.1.
   Written by Keith Wood (kwood{at}iinet.com.au) June 2009.
   Available under the MIT (https://github.com/jquery/jquery/blob/master/MIT-LICENSE.txt) license. 
   Please attribute the author if you use it. */

(function($) { // Hide scope, no $ conflict

/* Real person manager. */
function RealPerson() {
	this._defaults = {
		length: 6, // Number of characters to use
		includeNumbers: false, // True to use numbers as well as letters
		regenerate: 'Click to change', // Instruction text to regenerate
		hashName: '{n}Hash' // Name of the hash value field to compare with,
			// use {n} to substitute with the original field name
	};
}

var CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
var DOTS = [
	['   *   ', '  * *  ', '  * *  ', ' *   * ', ' ***** ', '*     *', '*     *'],
	['****** ', '*     *', '*     *', '****** ', '*     *', '*     *', '****** '],
	[' ***** ', '*     *', '*      ', '*      ', '*      ', '*     *', ' ***** '],
	['****** ', '*     *', '*     *', '*     *', '*     *', '*     *', '****** '],
	['*******', '*      ', '*      ', '****   ', '*      ', '*      ', '*******'],
	['*******', '*      ', '*      ', '****   ', '*      ', '*      ', '*      '],
	[' ***** ', '*     *', '*      ', '*      ', '*   ***', '*     *', ' ***** '],
	['*     *', '*     *', '*     *', '*******', '*     *', '*     *', '*     *'],
	['*******', '   *   ', '   *   ', '   *   ', '   *   ', '   *   ', '*******'],
	['      *', '      *', '      *', '      *', '      *', '*     *', ' ***** '],
	['*     *', '*   ** ', '* **   ', '**     ', '* **   ', '*   ** ', '*     *'],
	['*      ', '*      ', '*      ', '*      ', '*      ', '*      ', '*******'],
	['*     *', '**   **', '* * * *', '*  *  *', '*     *', '*     *', '*     *'],
	['*     *', '**    *', '* *   *', '*  *  *', '*   * *', '*    **', '*     *'],
	[' ***** ', '*     *', '*     *', '*     *', '*     *', '*     *', ' ***** '],
	['****** ', '*     *', '*     *', '****** ', '*      ', '*      ', '*      '],
	[' ***** ', '*     *', '*     *', '*     *', '*   * *', '*    * ', ' **** *'],
	['****** ', '*     *', '*     *', '****** ', '*   *  ', '*    * ', '*     *'],
	[' ***** ', '*     *', '*      ', ' ***** ', '      *', '*     *', ' ***** '],
	['*******', '   *   ', '   *   ', '   *   ', '   *   ', '   *   ', '   *   '],
	['*     *', '*     *', '*     *', '*     *', '*     *', '*     *', ' ***** '],
	['*     *', '*     *', ' *   * ', ' *   * ', '  * *  ', '  * *  ', '   *   '],
	['*     *', '*     *', '*     *', '*  *  *', '* * * *', '**   **', '*     *'],
	['*     *', ' *   * ', '  * *  ', '   *   ', '  * *  ', ' *   * ', '*     *'],
	['*     *', ' *   * ', '  * *  ', '   *   ', '   *   ', '   *   ', '   *   '],
	['*******', '     * ', '    *  ', '   *   ', '  *    ', ' *     ', '*******'],
	['  ***  ', ' *   * ', '*   * *', '*  *  *', '* *   *', ' *   * ', '  ***  '],
	['   *   ', '  **   ', ' * *   ', '   *   ', '   *   ', '   *   ', '*******'],
	[' ***** ', '*     *', '      *', '     * ', '   **  ', ' **    ', '*******'],
	[' ***** ', '*     *', '      *', '    ** ', '      *', '*     *', ' ***** '],
	['    *  ', '   **  ', '  * *  ', ' *  *  ', '*******', '    *  ', '    *  '],
	['*******', '*      ', '****** ', '      *', '      *', '*     *', ' ***** '],
	['  **** ', ' *     ', '*      ', '****** ', '*     *', '*     *', ' ***** '],
	['*******', '     * ', '    *  ', '   *   ', '  *    ', ' *     ', '*      '],
	[' ***** ', '*     *', '*     *', ' ***** ', '*     *', '*     *', ' ***** '],
	[' ***** ', '*     *', '*     *', ' ******', '      *', '     * ', ' ****  ']];

$.extend(RealPerson.prototype, {
	/* Class name added to elements to indicate already configured with real person. */
	markerClassName: 'hasRealPerson',
	/* Name of the data property for instance settings. */
	propertyName: 'realperson',

	/* Override the default settings for all real person instances.
	   @param  options  (object) the new settings to use as defaults
	   @return  (RealPerson) this object */
	setDefaults: function(options) {
		$.extend(this._defaults, options || {});
		return this;
	},

	/* Attach the real person functionality to an input field.
	   @param  target   (element) the control to affect
	   @param  options  (object) the custom options for this instance */
	_attachPlugin: function(target, options) {
		target = $(target);
		if (target.hasClass(this.markerClassName)) {
			return;
		}
		var inst = {options: $.extend({}, this._defaults)};
		target.addClass(this.markerClassName).data(this.propertyName, inst);
		this._optionPlugin(target, options);
	},

	/* Retrieve or reconfigure the settings for a control.
	   @param  target   (element) the control to affect
	   @param  options  (object) the new options for this instance or
	                    (string) an individual property name
	   @param  value    (any) the individual property value (omit if options
	                    is an object or to retrieve the value of a setting)
	   @return  (any) if retrieving a value */
	_optionPlugin: function(target, options, value) {
		target = $(target);
		var inst = target.data(this.propertyName);
		if (!options || (typeof options == 'string' && value == null)) { // Get option
			var name = options;
			options = (inst || {}).options;
			return (options && name ? options[name] : options);
		}

		if (!target.hasClass(this.markerClassName)) {
			return;
		}
		options = options || {};
		if (typeof options == 'string') {
			var name = options;
			options = {};
			options[name] = value;
		}
		$.extend(inst.options, options);
		target.prevAll('.' + this.propertyName + '-challenge,.' + this.propertyName + '-hash').
			remove().end().before(this._generateHTML(target, inst));
	},

	/* Generate the additional content for this control.
	   @param  target  (jQuery) the input field
	   @param  inst    (object) the current instance settings
	   @return  (string) the additional content */
	_generateHTML: function(target, inst) {
		var text = '';
		for (var i = 0; i < inst.options.length; i++) {
			text += CHARS.charAt(Math.floor(Math.random() *
				(inst.options.includeNumbers ? 36 : 26)));
		}
		var html = '<div class="' + this.propertyName + '-challenge">' +
			'<div class="' + this.propertyName + '-text">';
		for (var i = 0; i < DOTS[0].length; i++) {
			for (var j = 0; j < text.length; j++) {
				html += DOTS[CHARS.indexOf(text.charAt(j))][i].replace(/ /g, '&nbsp;') +
					'&nbsp;&nbsp;';
			}
			html += '<br>';
		}
		html += '</div><div class="' + this.propertyName + '-regen">' + inst.options.regenerate +
			'</div></div><input type="hidden" class="' + this.propertyName + '-hash" name="' +
			inst.options.hashName.replace(/\{n\}/, target.attr('name')) +
			'" value="' + this._hash(text) + '">';
		return html;
	},

	/* Enable the plugin functionality for a control.
	   @param  target  (element) the control to affect */
	_enablePlugin: function(target) {
		target = $(target);
		if (!target.hasClass(this.markerClassName)) {
			return;
		}
		target.removeClass(this.propertyName + '-disabled').prop('disabled', false).
			prevAll('.' + this.propertyName + '-challenge').removeClass(this.propertyName + '-disabled');
	},

	/* Disable the plugin functionality for a control.
	   @param  target  (element) the control to affect */
	_disablePlugin: function(target) {
		target = $(target);
		if (!target.hasClass(this.markerClassName)) {
			return;
		}
		target.addClass(this.propertyName + '-disabled').prop('disabled', true).
			prevAll('.' + this.propertyName + '-challenge').addClass(this.propertyName + '-disabled');
	},

	/* Remove the plugin functionality from a control.
	   @param  target  (element) the control to affect */
	_destroyPlugin: function(target) {
		target = $(target);
		if (!target.hasClass(this.markerClassName)) {
			return;
		}
		target.removeClass(this.markerClassName).
			removeData(this.propertyName).
			prevAll('.' + this.propertyName + '-challenge,.' + this.propertyName + '-hash').remove();
	},

	/* Compute a hash value for the given text.
	   @param  value  (string) the text to hash
	   @return  the corresponding hash value */
	_hash: function(value) {
		var hash = 5381;
		for (var i = 0; i < value.length; i++) {
			hash = ((hash << 5) + hash) + value.charCodeAt(i);
		}
		return hash;
	}
});

// The list of commands that return values and don't permit chaining
var getters = [''];

/* Determine whether a command is a getter and doesn't permit chaining.
   @param  command    (string, optional) the command to run
   @param  otherArgs  ([], optional) any other arguments for the command
   @return  true if the command is a getter, false if not */
function isNotChained(command, otherArgs) {
	if (command == 'option' && (otherArgs.length == 0 ||
			(otherArgs.length == 1 && typeof otherArgs[0] == 'string'))) {
		return true;
	}
	return $.inArray(command, getters) > -1;
}

/* Attach the real person functionality to a jQuery selection.
   @param  options  (object) the new settings to use for these instances (optional) or
                    (string) the command to run (optional)
   @return  (jQuery) for chaining further calls or
            (any) getter value */
$.fn.realperson = function(options) {
	var otherArgs = Array.prototype.slice.call(arguments, 1);
	if (isNotChained(options, otherArgs)) {
		return plugin['_' + options + 'Plugin'].apply(plugin, [this[0]].concat(otherArgs));
	}
	return this.each(function() {
		if (typeof options == 'string') {
			if (!plugin['_' + options + 'Plugin']) {
				throw 'Unknown command: ' + options;
			}
			plugin['_' + options + 'Plugin'].apply(plugin, [this].concat(otherArgs));
		}
		else {
			plugin._attachPlugin(this, options || {});
		}
	});
};

/* Initialise the real person functionality. */
var plugin = $.realperson = new RealPerson(); // Singleton instance

$(document).on('click', 'div.' + plugin.propertyName + '-challenge', function() {
	if (!$(this).hasClass(plugin.propertyName + '-disabled')) {
		$(this).nextAll('.' + plugin.markerClassName).realperson('option', {});
	}
});

})(jQuery);
