
openerp.base.form = function (openerp) {

openerp.base.FormView =  openerp.base.Controller.extend({
    init: function(session, element_id, dataset, view_id) {
        this._super(session, element_id);
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;
        this.fields_views = {};
        this.widgets = {};
        this.widgets_counter = 0;
        this.fields = {};
        this.datarecord = {};
        this.ready = false;
    },
    start: function() {
        //this.log('Starting FormView '+this.model+this.view_id)
        this.rpc("/base/formview/load", {"model": this.model, "view_id": this.view_id}, this.on_loaded);
    },
    on_loaded: function(data) {
        var self = this;
        this.fields_view = data.fields_view;
        //this.log(this.fields_view);

        var frame = new openerp.base.WidgetFrame(this, this.fields_view.arch);

        this.$element.html(QWeb.render("FormView", { "frame": frame, "view": this }));
        _.each(this.widgets, function(w) {
            w.start();
        });
        this.$element.find('button.form_save').click(this.do_save);

//        this.dataset.on_active_id.add(this.on_record_loaded);
//        this.dataset.active_id(fields of the form, this.on_record_loaded);
    },
    on_next: function() {
//        this.dataset.next();
//        this.dataset.active_id(fields of the form, this.on_record_loaded);
    },
    on_prev: function() {

//        this.dataset.prev();
//        this.dataset.active_id(fields of the form, this.on_record_loaded);
    },
    on_record_loaded: function(record) {
        this.datarecord = record;
        for (var f in this.fields) {
            this.fields[f].set_value(this.datarecord.values[f]);
        }
        this.on_form_changed();
        this.ready = true;
    },
    on_form_changed: function(widget) {
        for (var w in this.widgets) {
            w = this.widgets[w];
            w.process_attrs();
            w.update_dom();
        }
        if (widget) {
            // TODO: check if  and trigger
            // if (onchange for this field) {
            //      this.ready = false;
            //      rpc - process.callback ( this.ready = true; )
            // }
        }
    },
    do_save: function() {
        if (!this.ready) {
            return false;
        }
        var invalid = false;
        var values = {};
        for (var f in this.fields) {
            f = this.fields[f];
            if (f.invalid) {
                invalid = true;
            } else {
                values[f.name] = f.value;
            }
        }
        if (invalid) {
            this.on_invalid();
        } else {
            console.log("Save form", values);
            // TODO: save values via datarecord
            // rpc - save.callbacl on_saved
        }
    },
    on_invalid: function() {
    },
    on_saved: function() {
        // Check response for exceptions, display error
    }
});

openerp.base.Widget = openerp.base.Controller.extend({
    // TODO Change this to init: function(view, node) { and use view.session and a new element_id for the super
    // it means that widgets are special controllers
    init: function(view, node) {
        this.view = view;
        this.node = node;
        this.attrs = eval('(' + (this.node.attrs.attrs || '{}') + ')');
        this.type = this.type || node.tag;
        this.element_name = this.element_name || this.type;
        this.element_id = [this.view.element_id, this.element_name, this.view.widgets_counter++].join("_");

        this._super(this.view.session, this.element_id);

        this.view.widgets[this.element_id] = this;
        this.children = node.children;
        this.colspan = parseInt(node.attrs.colspan || 1);
        this.template = "Widget";

        this.string = this.string || node.attrs.string;
        this.help = this.help || node.attrs.help;
        this.invisible = (node.attrs.invisible == '1');
    },
    start: function() {
        this.$element = $('#' + this.element_id);
    },
    process_attrs: function() {
        for (var a in this.attrs) {
            this[a] = this.eval_attrs(this.attrs[a]);
        }
    },
    eval_attrs: function(expr) {
        var stack = [];
        for (var i = 0; i < expr.length; i++) {
            var ex = expr[i];
            if (ex.length == 1) {
                stack.push(ex[0]);
                continue;
            }

            var field = this.view.fields[ex[0]].value;
            var op = ex[1];
            var val = ex[2];

            switch (op.toLowerCase()) {
                case '=':
                case '==':
                    stack.push(field == val);
                    break;
                case '!=':
                case '<>':
                    stack.push(field != val);
                    break;
                case '<':
                    stack.push(field < val);
                    break;
                case '>':
                    stack.push(field > val);
                    break;
                case '<=':
                    stack.push(field <= val);
                    break;
                case '>=':
                    stack.push(field >= val);
                    break;
                case 'in':
                    stack.push(_.indexOf(val, field) > -1);
                    break;
                case 'not in':
                    stack.push(_.indexOf(val, field) == -1);
                    break;
                default:
                    this.log("Unsupported operator in attrs :", op);
            }
        }

        for (var j = stack.length-1; j >- 1; j--) {
            switch (stack[j]) {
                case '|':
                    var result = stack[j + 1] || stack[j + 2];
                    stack.splice(j, 3, result);
                    break;
                case '&':
                    var result = stack[j + 1] && stack[j + 2];
                    stack.splice(j, 3, result);
                    break;
            }
        }
        return _.indexOf(stack, false) == -1;
    },
    update_dom: function() {
        this.$element.toggle(!this.invisible);
    },
    render: function() {
        var template = this.template;
        return QWeb.render(template, { "widget": this });
    }
});

openerp.base.WidgetFrame = openerp.base.Widget.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "WidgetFrame";
        this.columns = node.attrs.col || 4;
        this.x = 0;
        this.y = 0;
        this.table = [];
        this.add_row();
        for (var i = 0; i < node.children.length; i++) {
            var n = node.children[i];
            if (n.tag == "newline") {
                this.add_row();
            } else {
                this.handle_node(n);
            }
        }
        this.set_row_cells_with(this.table[this.table.length - 1]);
    },
    add_row: function(){
        if (this.table.length) {
            this.set_row_cells_with(this.table[this.table.length - 1]);
        }
        var row = [];
        this.table.push(row);
        this.x = 0;
        this.y += 1;
        return row;
    },
    set_row_cells_with: function(row) {
        for (var i = 0; i < row.length; i++) {
            var w = row[i];
            if (w.is_field_label) {
                w.width = "1%";
                if (row[i + 1]) {
                    row[i + 1].width = Math.round((100 / this.columns) * (w.colspan + 1) - 1) + '%';
                }
            } else if (w.width === undefined) {
                w.width = Math.round((100 / this.columns) * w.colspan) + '%';
            }
        }
    },
    handle_node: function(n) {
        var type = this.view.fields_view.fields[n.attrs.name] || {};
        var widget_type = n.attrs.widget || type.type || n.tag;
        if (openerp.base.widgets[widget_type]) {
            var widget = new openerp.base.widgets[widget_type](this.view, n);
            if (n.tag == 'field' && n.attrs.nolabel != '1') {
                var label = new openerp.base.widgets['label'](this.view, n);
                label["for"] = widget;
                this.add_widget(label);
            }
            this.add_widget(widget);
        } else {
            this.log("Unhandled widget type : " + widget_type, n);
        }
    },
    add_widget: function(w) {
        if (!w.invisible) {
            var current_row = this.table[this.table.length - 1];
            if (current_row.length && (this.x + w.colspan) > this.columns) {
                current_row = this.add_row();
            }
            current_row.push(w);
            this.x += w.colspan;
        }
        return w;
    }
});

openerp.base.WidgetNotebook = openerp.base.Widget.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "WidgetNotebook";
        this.pages = [];
        for (var i = 0; i < node.children.length; i++) {
            var n = node.children[i];
            if (n.tag == "page") {
                var page = new openerp.base.WidgetFrame(this.view, n);
                this.pages.push(page);
            }
        }
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element.tabs();
    }
});

openerp.base.WidgetSeparator = openerp.base.Widget.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "WidgetSeparator";
    }
});

openerp.base.WidgetButton = openerp.base.Widget.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "WidgetButton";
    }
});

openerp.base.WidgetLabel = openerp.base.Widget.extend({
    init: function(view, node) {
        this.is_field_label = true;
        this.element_name = 'label_' + node.attrs.name;

        this._super(view, node);

        this.template = "WidgetLabel";
        this.colspan = 1;
    },
    render: function () {
        if (this['for'] && this.type !== 'label') {
            return QWeb.render(this.template, {widget: this['for']});
        }
        // Actual label widgets should not have a false and have type label
        return QWeb.render(this.template, {widget: this});
    }
});

openerp.base.Field = openerp.base.Widget.extend({
    init: function(view, node) {
        this.name = node.attrs.name;
        this.value = undefined;
        view.fields[this.name] = this;
        this.type = node.attrs.widget || view.fields_view.fields[node.attrs.name].type;
        this.element_name = "field_" + this.name + "_" + this.type;

        this._super(view, node);

        if (node.attrs.nolabel != '1' && this.colspan > 1) {
            this.colspan--;
        }
        // this.datarecord = this.view.datarecord ??
        this.field = view.fields_view.fields[node.attrs.name];
        this.string = node.attrs.string || this.field.string;
        this.help = node.attrs.help || this.field.help;
        this.nolabel = (node.attrs.nolabel == '1');
        this.readonly = (node.attrs.readonly == '1');
        this.required = (node.attrs.required == '1');
        this.invalid = false;
    },
    set_value: function(value) {
        this.value = value;
    },
    get_value: function(value) {
        return value;
    },
    update_dom: function() {
        this._super.apply(this, arguments);
        this.$element.toggleClass('disabled', this.readonly);
        this.$element.toggleClass('required', this.required);
    },
    on_ui_change: function() {
        this.view.on_form_changed(this);
    }
});

openerp.base.FieldChar = openerp.base.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldChar";
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element.find('input').change(this.on_ui_change);
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        if (value != null && value !== false) {
            this.$element.find('input').val(value);
        }
    },
    get_value: function() {
    },
    update_dom: function() {
        this._super.apply(this, arguments);
        this.$element.find('input').attr({
            'disabled' : this.readonly,
            'required' : this.required
        });
    },
    on_ui_change: function() {
        this.value = this.$element.find('input').val();
        this.invalid = this.required && this.value == "";
        this._super.apply(this, arguments);
    }
});

openerp.base.FieldEmail = openerp.base.FieldChar.extend({
});

openerp.base.FieldUrl = openerp.base.FieldChar.extend({
});

openerp.base.FieldFloat = openerp.base.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldChar";
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element.find('input').change(this.on_ui_change);
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        if (value != null && value !== false) {
            this.$element.find('input').val(value.toFixed(2));
        }
    },
    get_value: function() {
    },
    update_dom: function() {
        this._super.apply(this, arguments);
        this.$element.find('input').attr({
            'disabled' : this.readonly,
            'required' : this.required
        });
    },
    on_ui_change: function() {
        this.value = this.$element.find('input').val();
        this.invalid = this.required && this.value == "";
        this._super.apply(this, arguments);
    }
});

openerp.base.FieldText = openerp.base.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldText";
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        if (value != null && value !== false) {
            this.$element.find('textarea').val(value);
        }
    },
    get_value: function() {
        return this.$element.find('textarea').val();
    }
});

openerp.base.FieldBoolean = openerp.base.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldBoolean";
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        this.$element.find('input')[0].checked = value;
    },
    get_value: function() {
        return this.$element.find('input').is(':checked');
    }
});

openerp.base.FieldDate = openerp.base.FieldChar.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldDate";
    }
});

openerp.base.FieldDatetime = openerp.base.FieldChar.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldDatetime";
    }
});

openerp.base.FieldTextXml = openerp.base.Field.extend({
// to replace view editor
});

openerp.base.FieldSelection = openerp.base.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldSelection";
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        if (value != null && value !== false) {
            this.$element.find('select').val(value);
        }
    },
    get_value: function() {
        return this.$element.find('select').val();
    }
});

openerp.base.FieldMany2One = openerp.base.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldMany2One";
    }
});

openerp.base.FieldOne2Many = openerp.base.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldOne2Many";
    }
});

openerp.base.FieldMany2Many = openerp.base.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldMany2Many";
    }
});

openerp.base.FieldReference = openerp.base.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldReference";
    }
});

openerp.base.widgets = {
    'group' : openerp.base.WidgetFrame,
    'notebook' : openerp.base.WidgetNotebook,
    'separator' : openerp.base.WidgetSeparator,
    'label' : openerp.base.WidgetLabel,
    'char' : openerp.base.FieldChar,
    'email' : openerp.base.FieldEmail,
    'url' : openerp.base.FieldUrl,
    'text' : openerp.base.FieldText,
    'date' : openerp.base.FieldDate,
    'datetime' : openerp.base.FieldDatetime,
    'selection' : openerp.base.FieldSelection,
    'many2one' : openerp.base.FieldMany2One,
    'many2many' : openerp.base.FieldMany2Many,
    'one2many' : openerp.base.FieldOne2Many,
    'one2many_list' : openerp.base.FieldOne2Many,
    'reference' : openerp.base.FieldReference,
    'boolean' : openerp.base.FieldBoolean,
    'float' : openerp.base.FieldFloat,
    'button' : openerp.base.WidgetButton
};

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
