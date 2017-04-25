odoo.define('playground.demo', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');


var IncDecWidget = Widget.extend({
    template: 'IncrementDecrementAction',
    events: {
    	'click .o_inc_dec_action': '_onActionButtonClicked',
    },
    init: function (parent) {
        this._super.apply(this, arguments);
        this.set('data', 1);
        this.on('change:data', this, function() {
            this.$(".quantity").val(this.get('data'));
        });
    },
    /**
    -----------------------------------------
		Handlers
	---------------------------------------------		
    */
    _onActionButtonClicked: function(event) {
    	var self = this;
    	console.log("Inside _onActionButtonClicked ::: ");
    	event.preventDefault();
    	var actionType = $(event.currentTarget).data('type');
    	switch (actionType) {
    		case 'increment':
    			self.set('data', self.get('data')+1);
    			break;
    		case 'decrement':
    			self.set('data', self.get('data')-1);
    			break;
    	}
    }
});


var IncrementDecrementWidgetHandler = Widget.extend({
	template: 'IncrementDecrementWidgetHandler',
	events: {
    	'click .o_add_counter': '_onAddCounter',
    },
    init: function() {
    	this._super.apply(this, arguments);
    },
    start: function() {
    	this._super.apply(this, arguments);
    	var counterWidget = new IncDecWidget(this);
    	counterWidget.appendTo(this.$('.o_inc_dec_manager'));
    },

    /** -----------------------------------------
		Handlers
		-----------------------------------------
	*/
	_onAddCounter: function() {

	}
});

core.action_registry.add('inc.dec.demo', IncrementDecrementWidgetHandler);

});