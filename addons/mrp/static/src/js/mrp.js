odoo.define('mrp.mrp_state', function (require) {
var core = require('web.core');
var common = require('web.form_common');
var Model = require('web.Model');
var time = require('web.time');
var formats = require('web.formats');
var _t = core._t;


var SetBulletStatus = common.AbstractField.extend(common.ReinitializeFieldMixin,{
    init: function(field_manager, node) {
        this._super(field_manager, node);
        this.classes = this.options && this.options.classes || {};
    },
    render_value: function() {
        this._super.apply(this, arguments);
        if (this.get("effective_readonly")) {
            var bullet_class = this.classes[this.get('value')] || 'default';
            if (this.get('value')){
                title = this.get('value') == 'waiting'? _t('Waiting Materials') : _t('Ready to produce'),
                this.$el.attr({'title': title, 'style': 'display:inline'});
                this.$el
                    .removeClass('text-success text-danger text-default')
                this.$el.html($('<span>' + title + '</span>').addClass('label label-' + bullet_class));
            }
        }
    },
});

var TimeCounter = common.AbstractField.extend(common.ReinitializeWidgetMixin, common.ReinitializeFieldMixin,{
    init: function(field_manager, node){
        this._super(field_manager, node);
    },
    start: function(){
        var self = this;
        var super_result = this._super();
        this.field_manager.on("view_content_has_changed", this, function() {
            self.render_value();
        });
        return super_result;
    },
    render_value: function() {
        this._super.apply(this, arguments);
        var self = this;
        var timerId;
        this.result;
        var domain = [['workorder_id', '=', this.field_manager.datarecord.id],['user_id', '=', self.session.uid]];
        var model = new Model('mrp.workcenter.productivity').call('search_read', [domain, []]).then(function(result){
            self.result = result;
            if (self.get("effective_readonly")) {
            var minutes = 0;
            var second = 0;
            var time_count = [];
            var current_date = new Date();
            self.$el.removeClass('o_form_field_empty');
            _.each(self.result, function(data){
                var start = new Date(data.date_start);
                var end  = new Date(data.date_end);
                if (data.date_end != false){
                    time_count = update_counter(end - start);
                    if (time_count){
                        minutes += parseInt(time_count[0]);
                        second += parseInt(time_count[1]);
                    }
                }
                else {
                    time_count = update_counter(current_date - time.auto_str_to_date(data.date_start));
                    if (time_count){
                        minutes += parseInt(time_count[0]);
                        second += parseInt(time_count[1]);
                    }
                }
            });
            if (second >= 60){
                minutes += Math.floor(second/60);
                second = second%60;
            }
            function timeCounter(){
                second += 1;
                if (second >= 60){
                    minutes += Math.floor(second/60);
                    second = second%60;
                }
                var pattern = '%02d:%02d';
                var times  = _.str.sprintf(pattern, minutes, second);
                if (self.field_manager.datarecord.show_state == true){
                    self.$el.html($('<span>' + times + '</span>'));
                    timerId = setTimeout(function(){timeCounter()} ,1000)
                } else {
                    clearTimeout(timerId);
                    timerId = null;
                    var times = formats.format_value(self.field_manager.datarecord.delay, { type : 'float_time' });
                    self.$el.html($('<span>' + times + '</span>'));
                }
            }
            timeCounter();
        }
        });

        function update_counter(date){
            mins=Math.floor(((date%(60*60*1000*24))%(60*60*1000))/(60*1000)*1);
            secs=Math.floor((((date%(60*60*1000*24))%(60*60*1000))%(60*1000))/1000*1);
            return [mins, secs];
        }
    },

});

core.form_widget_registry.add('bullet_state', SetBulletStatus);
core.form_widget_registry.add('mrp_time_counter', TimeCounter);
});