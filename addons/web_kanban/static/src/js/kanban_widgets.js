odoo.define('web_kanban.widgets', function (require) {
"use strict";

var core = require('web.core');
var ProgressBar = require('web.ProgressBar');
var pyeval = require('web.pyeval');
var Registry = require('web.Registry');
var session = require('web.session');
var Widget = require('web.Widget');

var QWeb = core.qweb;
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

var Priority = AbstractField.extend({
    init: function(parent, field, $node) {
        this._super.apply(this, arguments);
        this.name = $node.attr('name');
    },
    prepare_priority: function() {
        var self = this;
        var selection = this.field.selection || [];
        var init_value = selection && selection[0][0] || 0;
        var data = _.map(selection.slice(1), function(element, index) {
            var value = {
                'value': element[0],
                'name': element[1],
                'click_value': element[0],
            };
            if (index === 0 && self.get('value') == element[0]) {
                value.click_value = init_value;
            }
            return value;
        });
        return data;
    },
    renderElement: function() {
        this.priorities = this.prepare_priority();
        var readonly = this.field && this.field.readonly;
        if (readonly){
            this.set('readonly', true);
        }
        this.$el = $(QWeb.render("Priority", {'widget': this}));
        if (!readonly){
            this.$el.on('click', 'a', this.do_action.bind(this));
        }
    },
    do_action: function(event) {
        event.preventDefault();
        var $a = $(event.currentTarget);
        var data = {};
        data[this.name] = String($a.data('value'));
        this.trigger_up('kanban_update_record', data);
    },
});

var KanbanSelection = AbstractField.extend({

    init: function(parent, field, $node) {
        this._super.apply(this, arguments);
        this.name = $node.attr('name');
        this.parent = parent;
    },
    prepare_dropdown_selection: function() {
        var self = this;
        var data = [];
        _.map(this.field.selection || [], function(res) {
            var value = {
                'name': res[0],
                'tooltip': res[1],
                'state_name': res[1],
            };
            var leg_opt = self.options && self.options.states_legend || null;
            if (leg_opt) {
                var key = leg_opt[value.name];
                var legend = self.parent.group_info[key];
                if (legend) {
                    value.state_name = legend;
                    value.tooltip = legend;
                }
            }
            if (res[0] == 'normal') { value.state_class = 'oe_kanban_status'; }
            else if (res[0] == 'done') { value.state_class = 'oe_kanban_status oe_kanban_status_green'; }
            else { value.state_class = 'oe_kanban_status oe_kanban_status_red'; }
            data.push(value);
        });
        return data;
    },
    renderElement: function() {
        var self = this;
        this.states = this.prepare_dropdown_selection();

        var state;
        for(var i = 0 ; i < this.states.length ; i++) {
            if(this.states[i].name === this.get('value')) {
                state = this.states[i];
            }
        }

        this.$el = $(QWeb.render("KanbanSelection", {'widget': this}));
        this.$('a').first().find('span').removeClass().addClass(state.state_class);
        this.$('ul li').show().filter(function() {
            return ($(this).data('value') === state.name);
        }).hide();

        this.$('a').click(function (ev) {
            ev.preventDefault();
        });

        this.$('li').click(this.set_kanban_selection.bind(this));
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
 * options
 * - editable: boolean if current_value is editable
 * - current_value: get the current_value from the field that must be present in the view
 * - max_value: get the max_value from the field that must be present in the view
 * - title: title of the gauge, displayed on top of the gauge
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
            title: this.options.title,
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

var fields_registry = new Registry();

fields_registry
    .add('priority', Priority)
    .add('kanban_state_selection', KanbanSelection)
    .add("attachment_image", KanbanAttachmentImage)
    .add('progress', KanbanProgressBar);

return {
    AbstractField: AbstractField,
    registry: fields_registry,
};

});
