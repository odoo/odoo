console.log('Stupid widget');

odoo.define('crm.crm_tooltip', function(require) {
"use strict";


/*
 * This widget use HTML data as tooltip message
 * /!\ the value has to be a SAFE html
 */

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var registry = require('web.field_registry');
var qweb = core.qweb;
var _t = core._t;

var CrmTooltip = AbstractField.extend({
    _render: function () {
        this.$el.html(qweb.render('crm_tooltip', {widget: this}));
        this.$el.find('i').popover({'trigger': 'hover', 'container': 'body'});
    },
});

registry.add("crm_tooltip", CrmTooltip);

});
