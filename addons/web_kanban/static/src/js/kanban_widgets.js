odoo.define('web_kanban.widgets', function (require) {
"use strict";

var core = require('web.core');
var formats = require('web.formats');
var Priority = require('web.Priority');
var ProgressBar = require('web.ProgressBar');
var pyeval = require('web.pyeval');
var Registry = require('web.Registry');
var session = require('web.session');
var Widget = require('web.Widget');
var QWeb = core.qweb;
var _t = core._t;
/**
 * Interface to be implemented by kanban fields.
 *
 */
var FieldInterface = {
    /**
        Constructor.
        - parent: The widget's parent.
        - field: A dictionary giving details about the field, including the current field's value in the
            raw_value field.
        - $node: The field <field> tag as it appears in the view, encapsulated in a jQuery object.
    */
    init: function(parent, field, $node) {},
};

/**
 * Abstract class for classes implementing FieldInterface.
 *
 * Properties:
 *     - value: useful property to hold the value of the field. By default, the constructor
 *     sets value property.
 *
 */
var AbstractField = Widget.extend(FieldInterface, {
    /**
        Constructor that saves the field and $node parameters and sets the "value" property.
    */
    init: function(parent, field, $node) {
        this._super(parent);
        this.field = field;
        this.$node = $node;
        this.options = pyeval.py_eval(this.$node.attr("options") || '{}');
        this.set("value", field.raw_value);
    },
});

var FormatChar = AbstractField.extend({
    tagName: 'span',
    init: function(parent, field, $node) {
        this._super.apply(this, arguments);
        this.format_descriptor = _.extend({}, this.field, {'widget': this.$node.attr('widget')});
    },
    renderElement: function() {
        this.$el.text(formats.format_value(this.field.raw_value, this.format_descriptor));
    }
});


var KanbanPriority = AbstractField.extend({
    init: function(parent, field, $node) {
        this._super.apply(this, arguments);
        this.name = $node.attr('name');
    },
    renderElement: function() {
        this._super();
        this.set('readonly', !!(this.field && this.field.readonly));
    },
    start: function() {
        this.priority = new Priority(this, {
            readonly: this.get('readonly'),
            value: this.get('value'),
            values: this.field.selection || [],
        });

        this.priority.on('update', this, function(update) {
            var data = {};
            data[this.name] = update.value;
            this.trigger_up('kanban_update_record', data);
        });

        this.on('change:readonly', this, function() {
            this.priority.readonly = this.get('readonly');
            var $div = $('<div/>').insertAfter(this.$el);
            this.priority.replace($div);
            this.setElement(this.priority.$el);
        });

        var self = this;
        return $.when(this._super(), this.priority.appendTo('<div>').done(function() {
            self.priority.$el.addClass(self.$el.attr('class'));
            self.replaceElement(self.priority.$el);
        }));
    },
});

var KanbanSelection = AbstractField.extend({

    init: function(parent, field, $node) {
        this._super.apply(this, arguments);
        this.name = $node.attr('name');
        this.parent = parent;
    },
    // Instead of making several rpc calls for each kanban card, take the values from the related fields on the tasks
    prepare_dropdown_selection: function() {
        var self = this;
        var _data = [];
        var stage_id = self.parent.values.stage_id.value[0];
        var stage_data = {
            id: stage_id,
            legend_normal: self.parent.values.legend_normal ? self.parent.values.legend_normal.value : undefined,
            legend_blocked: self.parent.values.legend_blocked ? self.parent.values.legend_blocked.value: undefined, 
            legend_done: self.parent.values.legend_done ? self.parent.values.legend_done.value: undefined,
        };
        _.map(self.field.selection || [], function(res) {
            var value = {
                'name': res[0],
                'tooltip': res[1],
            };
            if (res[0] === 'normal') {
                value.state_name = stage_data.legend_normal ? stage_data.legend_normal : res[1];
            } else if (res[0] === 'done') {
                value.state_class = 'oe_kanban_status_green'; 
                value.state_name = stage_data.legend_done ? stage_data.legend_done : res[1];
            } else { 
                value.state_class = 'oe_kanban_status_red'; 
                value.state_name = stage_data.legend_blocked ? stage_data.legend_blocked : res[1];
            }
            _data.push(value);
        });
        return _data;
    },
    renderElement: function() {
        var self = this;
        var state;
        self.states = this.prepare_dropdown_selection();

        var current_state = _.find(this.states, function(state) {
            return state.name === self.get('value');
        });

        self.$el = $(QWeb.render("KanbanSelection", {
            current_state_class: current_state.state_class,
            states: _.without(this.states, current_state)
        }));
        self.$('a').click(function (ev) {
            ev.preventDefault();
        });
        self.$('a').click(self.set_kanban_selection.bind(self));
    },
    set_kanban_selection: function(e) {
        e.preventDefault();
        var self = this;
        var $li = $(e.target).closest( "li" );
        if ($li.length) {
            var value = {};
            value[self.name] = String($li.data('value'));
            this.trigger_up('kanban_update_record', value, this);
        }
    },
});

var KanbanAttachmentImage =  AbstractField.extend({
    template: 'KanbanAttachmentImage',
});


/**
 * Kanban widgets: ProgressBar
 * parameters
 * - title: title of the gauge, displayed on top of the gauge
 * options
 * - editable: boolean if current_value is editable
 * - current_value: get the current_value from the field that must be present in the view
 * - max_value: get the max_value from the field that must be present in the view
 * - title: title of the gauge, displayed on top of the gauge --> not translated,  use parameter "title" instead
 * - on_change: action to call when cliking and setting a value
 */
var KanbanProgressBar = AbstractField.extend({
    events: {
        'click': function() {
            if(!this.readonly && this.progressbar.readonly) {
                this.toggle_progressbar();
            }
        }
    },

    init: function (parent, field, node) {
        this._super(parent, field, node);

        var record = this.getParent().record;
        this.progressbar = new ProgressBar(this, {
            readonly: true,
            value: record[this.options.current_value].raw_value,
            max_value: record[this.options.max_value].raw_value,
            title: _t(node && node[0].title || this.options.title),
            edit_max_value: this.options.edit_max_value,
        });

        this.readonly = !this.options.editable;
        this.on_change = this.options.on_change;
    },

    start: function () {
        var self = this;

        var def = this.progressbar.appendTo('<div>').done(function() {
            self.progressbar.$el.addClass(self.$el.attr('class'));
            self.replaceElement(self.progressbar.$el);
        });

        return $.when(this._super(), def).then(function() {
            if(!self.readonly) {
                var parent = self.getParent();
                self.progressbar.on('update', self, function(update) {
                    var value = update.changed_value;
                    if(!isNaN(value)) {
                        var data = {
                            method: this.on_change,
                            params: [parent.id, value],
                            callback: self.proxy('toggle_progressbar'),
                        };
                        self.trigger_up('kanban_call_method', data);

                        // parent.view.dataset.call(this.on_change, [parent.id, value]).then(function() {
                        //     self.toggle_progressbar();
                        // });
                    } 
                });
            }
        });
    },

    toggle_progressbar: function() {
        this.progressbar.readonly = !this.progressbar.readonly;
        var $div = $('<div/>').insertAfter(this.$el);
        this.progressbar.replace($div);
        this.setElement(this.progressbar.$el);
    },
});

var KanbanMonetary = AbstractField.extend({
    tagName: 'span',
    renderElement: function() {
        var kanban_view = this.getParent();
        var currency_field = (this.options && this.options.currency_field) || 'currency_id';
        var currency_id = kanban_view.values[currency_field].value[0];
        var currency = session.get_currency(currency_id);
        var digits_precision = this.options.digits || (currency && currency.digits);
        var value = formats.format_value(this.field.raw_value || 0, {type: this.field.type, digits: digits_precision});
        if (currency) {
            if (currency.position === "after") {
                value += currency.symbol;
            } else {
                value = currency.symbol + value;
            }
        }
        this.$el.text(value);
    }
});

var fields_registry = new Registry();

fields_registry
    .add('priority', KanbanPriority)
    .add('kanban_state_selection', KanbanSelection)
    .add("attachment_image", KanbanAttachmentImage)
    .add('progress', KanbanProgressBar)
    .add('float_time', FormatChar)
    .add('monetary', KanbanMonetary)
    ;

return {
    AbstractField: AbstractField,
    registry: fields_registry,
};

});
