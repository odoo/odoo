odoo.define('pragtech_ppc_ganttchart.initialization_copy1',function(require) {
	"use strict";
	var AbstractAction = require('web.AbstractAction');
	var concurrency = require('web.concurrency');
	var Context = require('web.Context');
	var core = require('web.core');
	var Dialog = require('web.Dialog');
	var dom = require('web.dom');
	var framework = require('web.framework');
	var pyUtils = require('web.py_utils');
	var Widget = require('web.Widget');
	var ActionManager = require('web.ActionManager');

	var _t = core._t;
	
	
var InheritedAM2 = ActionManager.include({
	clearUncommittedChanges: function () {
        var currentController = this.getCurrentController();
        if (currentController){
	        if (currentController && currentController.widget.canBeRemoved) {
	            return currentController.widget.canBeRemoved();
	        }
        }
        return Promise.resolve();
    },
    
	});
	
});
