odoo.define('iot.floatinput', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');
var registry = require('web.field_registry');

var FieldFloat = require('web.basic_fields').InputField

var IotFieldFloat = FieldFloat.extend({
    className: 'o_field_iot o_field_float o_field_number',  //or do some extends
    tagName: 'span',

    events: _.extend(FieldFloat.prototype.events, {
        'click .o_button_iot': '_onButtonClick',
    }),


    init: function () {
        this._super.apply(this, arguments);
        if (this.mode === 'edit') {
            this.tagName = 'div';
            this.className += ' o_input';
        }
    },

    _renderEdit: function() {
        this.$el.empty();

        // Prepare and add the input
        this._prepareInput(this.$input).appendTo(this.$el);

        var $button = $('<button>', {class: 'o_button_iot btn-sm btn-primary'}).text('Take measure');
        $button.appendTo(this.$el);
    },


    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    _onButtonClick: function (ev) {
        var self = this;
        var ipField = this.nodeOptions.ip_field;
        var ip = this.record.data[ipField];
        
        var identifierField = this.nodeOptions.identifier_field;
        var identifier = this.record.data[identifierField];
        var composite_url = "http://"+ip+":8069/driverdetails/" + identifier;

        $.get(composite_url, function(data){
            self._setValue(data);
            self._render();
        });
    }



})
registry.add('iot', IotFieldFloat);

var ActionManager = require('web.ActionManager');
ActionManager.include({
    _executeReportAction: function (action, options) {
        if (action.device_id) {
        // Call new route that sends you report to send to printer
            console.log('Printing to IoT device...');
            var self = this;
            self.action=action;
            this._rpc({model: 'ir.actions.report',
                       method: 'iot_render',
                       args: [action.id, action.context.active_ids, {'device_id': action.device_id}]
                      }).then(function (result) {
                        var data = {action: 'print',
                                    type: result[1],
                                    data: result[2]};
                        $.ajax({ //code from hw_screen pos
                            type: 'POST',
                            url: result[0],
                            dataType: 'json',
                            beforeSend: function(xhr){xhr.setRequestHeader('Content-Type', 'application/json');},
                            data: JSON.stringify(data),
                            success: function(data) {
                                console.log('Printed successfully!');
                            }});
                        });
            return $.when();
        }
        else {
            return this._super.apply(this, arguments);
        }
    }
})




});


