odoo.define('mrp.mrp_state', function (require) {

var core = require('web.core');
var common = require('web.form_common');
var Model = require('web.Model');
var time = require('web.time');

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
                var title = this.get('value') == 'waiting'? _t('Waiting Materials') : _t('Ready to produce');
                this.$el.attr({'title': title, 'style': 'display:inline'});
                this.$el
                    .removeClass('text-success text-danger text-default')
                this.$el.html($('<span>' + title + '</span>').addClass('label label-' + bullet_class));
            }
        }
    },
});

var TimeCounter = common.AbstractField.extend(common.ReinitializeWidgetMixin, common.ReinitializeFieldMixin, {
    start: function() {
        this._super();
        var self = this;
        this.field_manager.on("view_content_has_changed", this, function () {
            self.render_value();
        });
    },
    render_value: function() {
        this._super.apply(this, arguments);
        var self = this;
        var timer, domain = [['workorder_id', '=', this.field_manager.datarecord.id], ['user_id', '=', self.session.uid]];
        new Model('mrp.workcenter.productivity').call('search_read', [domain, []]).then(function(result) {
            if (self.get("effective_readonly")) {
                self.$el.removeClass('o_form_field_empty');
                var current_date = new Date(), duration = 0;
                _.each(result, function(data) {
                    duration += data.date_end ? self.get_date_difference(data.date_start, data.date_end) : self.get_date_difference(time.auto_str_to_date(data.date_start), current_date);
                });
                function time_counter() {
                    if (self.field_manager.datarecord.show_state) {
                        duration += 1000;
                        timer = setTimeout(function() {
                            time_counter();
                        }, 1000);
                    } else {
                        clearTimeout(timer);
                    }
                    self.$el.html($('<span>' + moment.utc(duration).format("HH:mm:ss") + '</span>'));
                }
                time_counter();
            }
        });
    },
    get_date_difference: function(date_start, date_end) {
        var difference = moment(date_end).diff(moment(date_start));
        return moment.duration(difference);
    },
});

core.form_widget_registry.add('bullet_state', SetBulletStatus)
                         .add('mrp_time_counter', TimeCounter);
});
