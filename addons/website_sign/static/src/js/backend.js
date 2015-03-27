
odoo.define('website_sign.backend_iframe', function(require) {
	'use strict';

	var core = require('web.core');
	var Widget = require('web.Widget');

	var WIDGETS = {};

	WIDGETS.Dashboard = Widget.extend({
		tagName: "iframe",

		attributes: {
			'src': '/sign'
		},

		events: {
			'load': 'loadIframe'
		},

		loadIframe: function() {
			var $mainContent = this.$el.contents().find('body main').detach();
			if($mainContent.length > 0)
				$mainContent.appendTo(this.$el.contents().find('body').html(''));
		},

		start: function() {
			this.$el.css('border', 'none').css('width', '100%').css('height', '100%');
			return this._super();
		},
	});

	core.action_registry.add('website_sign.dashboard', WIDGETS.Dashboard);

	return WIDGETS;
});
