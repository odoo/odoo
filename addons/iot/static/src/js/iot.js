
odoo.define('iot.floatinput', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');
var registry = require('web.field_registry');
var widget_registry = require('web.widget_registry');
var Widget = require('web.Widget');
var FieldFloat = require('web.basic_fields').InputField;
var _t = core._t;


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
});

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
                                self.do_notify(_t('Successfully sent to printer!'));
                                //console.log('Printed successfully!');
                            },
                            error: function(data) {
                                self.do_warn(_t('Connection with the IoTBox failed!'));
                            },

                            });
                        });
            return $.when();
        }
        else {
            return this._super.apply(this, arguments);
        }
    }
});



var IotDetectButton = Widget.extend({
    tagName: 'button',
    className: 'o_iot_detect_button',
    events: {
        'click': '_onButtonClick',
    },

    find_proxy: function(options){
        options = options || {};
        var self  = this;
        var port  = ':' + (options.port || '8069');
        var urls  = [];
        var found = false;
        var parallel = 8;
        var done = new $.Deferred(); // will be resolved with the proxies valid urls
        var threads  = [];
        var progress = 0;

        urls.push('http://localhost'+port);
        for(var i = 0; i < 256; i++){
            urls.push('http://192.168.0.'+i+port);
            urls.push('http://192.168.1.'+i+port);
            urls.push('http://10.0.0.'+i+port);
        }

        var prog_inc = 1/urls.length;

        function update_progress(){
            progress = found ? 1 : progress + prog_inc;
            if(options.progress){
                options.progress(progress);
            }
        }

        function thread(done){
            var url = urls.shift();

            done = done || new $.Deferred();

            if( !url || found || !self.searching_for_proxy ){
                done.resolve();
                return done;
            }

            $.ajax({
                    url: url + '/hw_proxy/hello',
                    method: 'GET',
                    timeout: 400,
                }).done(function(){
                    //found = true;
                    update_progress();
                    done.resolve(url);
                })
                .fail(function(){
                    update_progress();
                    thread(done);
                });

            return done;
        }

        this.searching_for_proxy = true;

        var len  = Math.min(parallel,urls.length);
        for(i = 0; i < len; i++){
            threads.push(thread());
        }

        $.when.apply($,threads).then(function(){
            var urls = [];
            for(var i = 0; i < arguments.length; i++){
                if(arguments[i]){
                    urls.push(arguments[i]);
                }
            }
            console.log(urls);
            done.resolve(urls);
        });

        return done;
    },

    _onButtonClick: function(ev) {
        var self = this;

        var found_url = this.find_proxy({});

        // If url found, then try to connect to this IoT-box
        found_url.then(function (urls) {
            if (urls) {
                self._rpc({route: '/iot/base_url', params: {}}).then(function (result) {
                    self.server_url = result
                    for (var i = 0; i < urls.length; i++) {
                        self.url = urls[i];
                        console.log("Connecting to URL", self.url);
                        //send url to iotbox and check if the iotbox has already been connected or not
                        var full_url = self.url + '/box/connect';
                        $.ajax({
                            url: full_url,
                            data: {url: result},
                            method: 'GET',
                            //timeout: 400,
                        }).done(function (result2){
                            //something
                            console.log('Sent IoTBox:' + result2);
                        });
                    }
                });
            } //if url
        });

        found_url.fail(function () {
            console.log('No IoTBox found');
            //self._setValue("DISCONNECTED");
            //self._render();
        });
    },

});

widget_registry.add('iot_detect_button', IotDetectButton);
});


