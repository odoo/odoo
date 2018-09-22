odoo.define('iot.floatinput', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');
var registry = require('web.field_registry');
var widget_registry = require('web.widget_registry');
var FieldFloat = require('web.basic_fields').InputField;
var py_eval = require('web.py_utils').py_eval;
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

    _renderEdit: function () {
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
        var composite_url = "http://" + ip + ":8069/driverdetails/" + identifier;

        $.get(composite_url, function (data) {
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
            self.action = action;
            this._rpc({
                model: 'ir.actions.report',
                method: 'iot_render',
                args: [action.id, action.context.active_ids, {'device_id': action.device_id}]
            }).then(function (result) {
                var data = {
                    action: 'print',
                    type: result[1],
                    data: result[2]
                };
                $.ajax({ //code from hw_screen pos
                    type: 'POST',
                    url: result[0],
                    dataType: 'json',
                    beforeSend: function (xhr) {
                        xhr.setRequestHeader('Content-Type', 'application/json');
                    },
                    data: JSON.stringify(data),
                    success: function (data) {
                        self.do_notify(_t('Successfully sent to printer!'));
                        //console.log('Printed successfully!');
                    },
                    error: function (data) {
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
    className: 'o_iot_detect_button btn btn-primary',
    events: {
        'click': '_onButtonClick',
    },
    init: function (parent, record) {
        this._super.apply(this, arguments);
        this.token = record.data.token;
        this.parallelRPC = 8;
    },

    start: function () {
        this._super.apply(this, arguments);
        this.$el.text(_t('SCAN'));
    },

    _getUserIP: function (onNewIP) {
        //  onNewIp - your listener function for new IPs
        //compatibility for firefox and chrome
        var myPeerConnection = window.RTCPeerConnection || window.mozRTCPeerConnection || window.webkitRTCPeerConnection;
        var pc = new myPeerConnection({
            iceServers: []
        });
        var noop = function () {};
        var localIPs = {};
        var ipRegex = /([0-9]{1,3}(\.[0-9]{1,3}){3}|[a-f0-9]{1,4}(:[a-f0-9]{1,4}){7})/g;

        function iterateIP(ip) {
            if (!localIPs[ip]){
                if (ip.length < 16){
                    localIPs[ip] = true;
                    onNewIP(ip);
                }
            }
        }

        //create a bogus data channel
        pc.createDataChannel("");

        // create offer and set local description
        pc.createOffer().then(function (sdp) {
            sdp.sdp.split('\n').forEach(function (line) {
                if (line.indexOf('candidate') < 0) return;
                line.match(ipRegex).forEach(iterateIP);
            });

            pc.setLocalDescription(sdp, noop, noop);
        });

        //listen for candidate events
        pc.onicecandidate = function (ice) {
            if (!ice || !ice.candidate || !ice.candidate.candidate || !ice.candidate.candidate.match(ipRegex)) return;
            ice.candidate.candidate.match(ipRegex).forEach(iterateIP);
        };
    },

    _createThread: function (urls, range) {
        var self = this;
        var url = urls.shift();

        if (url){
            $.ajax({
                url: url + '/hw_proxy/hello',
                method: 'GET',
                timeout: 400,
            }).done(function () {
                self._addIOT(url);
                self._connectToIOT(url);
                if (range) self._updateRangeProgress(range);
            }).fail(function () {
                self._createThread(urls, range);
                if (range) self._updateRangeProgress(range);
            });
        }
    },

    _addIPRange: function (range, port){
        var ipPerRange = 256;

        var $range = $('<li/>').addClass('list-group-item').append('<b>' + range + '*' + '</b>');
        var $progress = $('<div class="progress"/>');
        var $bar = $('<div class="progress-bar" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"/>').css('width', '0%').text('0%');

        $progress.append($bar);
        $range.append($progress);

        this.ranges[range] = {
            $range: $range,
            $bar: $bar,
            urls: [],
            current: 0,
            total: ipPerRange,
        };
        this.$progressRanges.append($range);

        for (var i = 0; i < ipPerRange; i++) {
            this.ranges[range].urls.push('http://' + range + i + port);
        }
    },

    _processIRRange: function (range){
        var len = Math.min(this.parallelRPC, range.urls.length);
        for (var i = 0; i < len; i++) {
            this._createThread(range.urls, range);
        }
    },

    _updateRangeProgress: function (range) {
        range.current ++;
        var percent = Math.round(range.current / range.total * 100);
        range.$bar.css('width', percent + '%').attr('aria-valuenow', percent).text(percent + '%');
    },

    _findIOTs: function (options) {
        options = options || {};
        var self = this;
        var port = ':' + (options.port || '8069');
        var range;

        this._getUserIP(function (ip) {
            self._initProgress();

            self.searching_for_proxy = true;

            // Query localhost
            var local_url = 'http://localhost' + port;
            self._createThread([local_url]);

            // Process range by range
            if (ip) {
                range = ip.replace(ip.split('.')[3], '');
                self._addIPRange(range, port);
            }
            else {
                self._addIPRange('192.168.0.', port);
                self._addIPRange('192.168.1.', port);
                self._addIPRange('10.0.0.', port);
            }

            _.each(self.ranges, self._processIRRange, self);
        });
    },

    _initProgress: function (){
        this.$progressBlock = $('.scan_progress').show();
        this.$progressRanges = this.$progressBlock.find('.scan_ranges').empty();
        this.$progressFound = this.$progressBlock.find('.found_devices').empty();

        this.ranges = {};
        this.iots = {};
    },

    _addIOT: function (url){
        var $iot = $('<li/>')
            .addClass('list-group-item')
            .text(url)
            .append('<i class="fa fa-spinner fa-spin pull-right"/>');
        this.iots[url] = $iot;
        this.$progressFound.append($iot);
    },

    _updateIOT: function (url, message){
        if (this.iots[url]){
            var $i = this.iots[url].find('i').removeClass('fa-spinner fa-spin');
            if (message === 'IoTBox connected') $i.addClass('fa-check text-success');
            else $i.addClass('fa-exclamation-triangle text-danger');
            this.iots[url].append('<div>' + message + '</div>');
        }
    },

    _connectToIOT: function (url){
        var self = this;
        var full_url = url + '/box/connect';
        var json_data = {token: self.token};
        
        $.ajax({
            headers: {'Content-Type': 'application/json'},
            url: full_url,
            dataType: 'json',
            data: JSON.stringify(json_data),
            type: 'POST',
        }).done(function (response) {
            self._updateIOT(url, response.result);
        }).fail(function (){
            self._updateIOT(url, _t('Connection failed'));
        });
    },

    _onButtonClick: function (e) {
        this.$el.attr('disabled', true);
        this._findIOTs();
    },

});

widget_registry.add('iot_detect_button', IotDetectButton);


var IotTakeMeasureButton = Widget.extend({
    tagName: 'button',
    className: 'btn btn-primary',
    events: {
        'click': '_onButtonClick',
    },

    /**
     * @override
     */
    init: function (parent, record, node) {
        this.record = record;
        this.options = py_eval(node.attrs.options);
        this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments);
        this.$el.text(_t('Take Measure'));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onButtonClick: function (ev) {
        var self = this;
        var ip = this.record.data[this.options.ip_field];
        var identifier = this.record.data[this.options.identifier_field];
        var composite_url = "http://" + ip + ":8069/driverdetails/" + identifier;
        var measure_field = this.options.measure_field;

        $.get(composite_url, function (measure) {
            var changes = {};
            changes[measure_field] = parseFloat(measure);
            self.trigger_up('field_changed', {
                dataPointID: self.record.id,
                changes: changes,
            });
        });
    },
});

widget_registry.add('iot_take_measure_button', IotTakeMeasureButton);

});


