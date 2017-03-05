odoo.define('web.kanban_quick_create', function (require) {
"use strict";

var Widget = require('web.Widget');

var RecordQuickCreate = Widget.extend({
    template: "KanbanView.QuickCreate",

    events: {
        'click .o_kanban_cancel': function () {
            this.cancel();
        },
        'click .o_kanban_add': function () {
            this.add_record();
        },
        'keypress input': function (event) {
            if (event.keyCode === 13) {
                this.add_record();
            }
        },
        'keydown': function (event) {
            if (event.keyCode === 27) {
                this.cancel();
            }
        },
        'mousedown .o_kanban_add': 'suppress',
        'mousedown .o_kanban_cancel': 'suppress',
    },

    init: function (parent, width) {
        this._super.apply(this, arguments);
        this.width = width;
    },

    start: function () {
        this.$el.css({width: this.width});
        this.$input = this.$('input');
        this.$input.focus();
        return this._super.apply(this, arguments);
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
    suppress: function (e) {
        e.preventDefault();
    },
});

var ColumnQuickCreate = Widget.extend({
    template: 'KanbanView.ColumnQuickCreate',

    events: {
        'click': 'toggle',
        'click .o_kanban_add': function (event) {
            event.stopPropagation();
            this.add_column();
        },
        'click .o_kanban_cancel': function () {
            this.folded = true;
            this.update();
        },
        'click .o_kanban_quick_create': function (event) {
            event.stopPropagation();
        },
        'keypress input': function (event) {
            if (event.keyCode === 13) {
                this.add_column();
            }
        },
        'keydown': function (event) {
            if (event.keyCode === 27) {
                this.folded = true;
                this.update();
            }
        },
        'focusout': function () {
            var hasFocus = this.$(':focus').length > 0;
            if (hasFocus) { return; }

            this.folded = true;
            this.$input.val('');
            this.update();
        },
        'mousedown .o_kanban_add': 'suppress',
        'mousedown .o_kanban_cancel': 'suppress',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.folded = true;
    },

    start: function () {
        this.$header = this.$('.o_column_header');
        this.$quick_create = this.$('.o_kanban_quick_create');
        this.$input = this.$('input');
        return this._super.apply(this, arguments);
    },

    toggle: function () {
        this.folded = !this.folded;
        this.update();
        if (!this.folded) {
            this.$input.focus();
            this.trigger_up('scrollTo', {selector: '.o_column_quick_create'});
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
    },
    suppress: function (e) {
        e.preventDefault();
    },
});

return {
    RecordQuickCreate: RecordQuickCreate,
    ColumnQuickCreate: ColumnQuickCreate,
};

});
