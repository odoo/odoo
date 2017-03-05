odoo.define('mrp.mrp_state', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var time = require('web.time');
var field_registry = require('web.field_registry');

var _t = core._t;


var SetBulletStatus = AbstractField.extend({
    supportedFieldTypes: ['selection'],
    init: function() {
        this._super.apply(this, arguments);
        this.classes = this.nodeOptions && this.nodeOptions.classes || {};
    },
    render_readonly: function() {
        this._super.apply(this, arguments);
        var bullet_class = this.classes[this.value] || 'default';
        if (this.value){
            var title = this.value === 'waiting'? _t('Waiting Materials') : _t('Ready to produce');
            this.$el.attr({'title': title, 'style': 'display:inline'});
            this.$el.removeClass('text-success text-danger text-default');
            this.$el.html($('<span>' + title + '</span>').addClass('label label-' + bullet_class));
        }
    }
});

var TimeCounter = AbstractField.extend({
    supportedFieldTypes: ['float'],
    start_time_counter: function(){
        var self = this;
        clearTimeout(this.timer);
        if (this.record.data.is_user_working) {
            this.duration += 1000;
            this.timer = setTimeout(function() {
                self.start_time_counter();
            }, 1000);
        } else {
            clearTimeout(this.timer);
        }
        this.$el.html($('<span>' + moment.utc(this.duration).format("HH:mm:ss") + '</span>'));
    },
    render: function() {
        var self = this;
        this._super.apply(this, arguments);
        var productivity_domain = [['workorder_id', '=', this.record.data.id], ['user_id', '=', self.session.uid]];
        this.trigger_up('perform_model_rpc', {
            method: 'search_read',
            model: 'mrp.workcenter.productivity',
            args: [productivity_domain, []],
            on_success: function (result) {
                if (self.mode === "readonly") {
                    var current_date = new Date();
                    self.duration = 0;
                    _.each(result, function(data) {
                        self.duration += data.date_end ? self.get_date_difference(data.date_start, data.date_end) : self.get_date_difference(time.auto_str_to_date(data.date_start), current_date);
                    });
                    self.start_time_counter();
                }
            },
        });
    },
    get_date_difference: function(date_start, date_end) {
        var difference = moment(date_end).diff(moment(date_start));
        return moment.duration(difference);
    },
    has_no_value: function() {
        return false;
    }
});

field_registry
    .add('bullet_state', SetBulletStatus)
    .add('mrp_time_counter', TimeCounter)
    .add('pdf_viewer', AbstractField); // TODO

});
