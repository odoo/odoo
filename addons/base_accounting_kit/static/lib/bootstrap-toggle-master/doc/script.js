+function ($) {
	'use strict';

	$('.example:not(.skip)').each(function() {
		// fetch & encode html
		var html = $('<div>').text($(this).html()).html()
		// find number of space/tabs on first line (minus line break)
		var count = html.match(/^(\s+)/)[0].length - 1
		// replace tabs/spaces on each lines with 
		var regex = new RegExp('\\n\\s{'+count+'}', 'g')
		var code = html.replace(regex, '\n').replace(/\t/g, '  ').trim()
		// other cleanup
		code = code.replace(/=""/g,'')
		// add code block to dom
		$(this).after( $('<code class="highlight html">').html(code) )
	});

	$('code.highlight').each(function() {
		hljs.highlightBlock(this)
	});

}(jQuery);

var Demo = function () {}

Demo.prototype.init = function(selector) {
	$(selector).bootstrapToggle(selector)
}
Demo.prototype.destroy = function(selector) {
	$(selector).bootstrapToggle('destroy')
}
Demo.prototype.on = function(selector) {
	$(selector).bootstrapToggle('on')
}
Demo.prototype.off = function(selector) {
	$(selector).bootstrapToggle('off')
}
Demo.prototype.toggle = function(selector) {
	$(selector).bootstrapToggle('toggle')
}
Demo.prototype.enable = function(selector) {
	$(selector).bootstrapToggle('enable')
}
Demo.prototype.disable = function(selector) {
	$(selector).bootstrapToggle('disable')
}


demo = new Demo()
