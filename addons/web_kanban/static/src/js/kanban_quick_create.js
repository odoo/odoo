odoo.define('web_kanban.quick_create', function (require) {
"use strict";

var Widget = require('web.Widget');

var RecordQuickCreate = Widget.extend({
    template: "KanbanView.QuickCreate",

    events: {
        'click .o_kanban_cancel': 'cancel',
        'click .o_kanban_add': 'add_record',
        'keypress input': function (event) {
            if (event.keyCode === 13) {
                this.add_record();
            }
        },
        'keydown': function (event) {
            if (event.keyCode === 27) {
                this.trigger_up('cancel_quick_create');
            }
        },
    },

    init: function (parent, width) {
        this._super(parent);
        this.width = width;
    },

    start: function () {
        this.$el.css({width: this.width});
        this.$input = this.$('input');
        this.$input.focus();
    },

    cancel: function () {
        this.trigger_up('cancel_quick_create');
    },

    add_record: function () {
        var value = this.$input.val();
        this.$input.val('');
        if (/^\s*$/.test(value)) { return; }
        this.trigger_up('quick_create_add_record', {value: value});
        this.$input.focus();
    },
});

var ColumnQuickCreate = Widget.extend({
    template: 'KanbanView.ColumnQuickCreate',

    events: {
        'click .o_kanban_add': function (event) {
            console.log('click okanbanadd');
            event.stopPropagation();
            this.add_column();
        },
        'click .o_kanban_quick_create': function (event) {
            console.log('click quickcreate');
            event.stopPropagation();
        },
        'keypress input': function (event) {
            if (event.keyCode === 13) {
                this.add_column();
            }
        },
        'click .o_kanban_cancel': function (event) {
            this.folded = true;
            this.update();
        },
        'keydown': function (event) {
            if (event.keyCode === 27) {
                this.folded = true;
                this.update();
            }
        },
    },

    init: function (parent) {
        this._super(parent);
        this.folded = true;
    },

    start: function () {
        this.$header = this.$('.o_column_header');
        this.$quick_create = this.$('.o_kanban_quick_create');
        this.$input = this.$('input');
        this.$el.click(this.proxy('toggle'));
        var self = this;
        this.$el.focusout(function () {
            setTimeout(function() {
                var hasFocus = !! (self.$(':focus').length > 0);
                if (! hasFocus) {
                    self.folded = true;
                    self.update();
                }
            }, 10);
        });
    },

    toggle: function () {
        this.folded = !this.folded;
        this.update();
        if (!this.folded) {
            this.$input.focus();
        }
    },

    update: function () {
        this.$header.toggle(this.folded);
        this.$quick_create.toggle(!this.folded);
    },

    add_column: function () {
        var name = this.$input.val();
        this.$input.val('');
        if (/^\s*$/.test(name)) { return; }
        this.trigger_up('quick_create_add_column', {value: name});
        this.$input.focus();
    }
});

return {
    RecordQuickCreate: RecordQuickCreate,
    ColumnQuickCreate: ColumnQuickCreate,
};

});
