
openerp.base.form = function (openerp) {

openerp.base.views.add('form', 'openerp.base.FormView');
openerp.base.FormView =  openerp.base.Controller.extend( /** @lends openerp.base.FormView# */{
    /**
     * Indicates that this view is not searchable, and thus that no search
     * view should be displayed (if there is one active).
     */
    searchable: false,
    /**
     * @constructs
     * @param {openerp.base.Session} session the current openerp session
     * @param {String} element_id this view's root element id
     * @param {openerp.base.DataSet} dataset the dataset this view will work with
     * @param {String} view_id the identifier of the OpenERP view object
     */
    init: function(session, element_id, dataset, view_id) {
        this._super(session, element_id);
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;
        this.fields_view = {};
        this.widgets = {};
        this.widgets_counter = 0;
        this.fields = {};
        this.datarecord = {};
        this.ready = false;
    },
    start: function() {
        //this.log('Starting FormView '+this.model+this.view_id)
        return this.rpc("/base/formview/load", {"model": this.model, "view_id": this.view_id}, this.on_loaded);
    },
    on_loaded: function(data) {
        var self = this;
        this.fields_view = data.fields_view;

        var frame = new openerp.base.form.WidgetFrame(this, this.fields_view.arch);

        this.$element.html(QWeb.render("FormView", { "frame": frame, "view": this }));
        _.each(this.widgets, function(w) {
            w.start();
        });
        this.$element.find('div.oe_form_pager button[data-pager-action]').click(function() {
            var action = $(this).data('pager-action');
            self.on_pager_action(action);
        });
    },
    on_record_loaded: function(record) {
        if (record.length) {
            this.datarecord = record[0];
            for (var f in this.fields) {
                this.fields[f].set_value(this.datarecord.values[f]);
            }
            this.on_form_changed();
            this.ready = true;
        }
        this.do_update_pager();
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
    do_show: function () {
        this.dataset.fetch_index(this.fields_view.fields, this.on_record_loaded);
        this.$element.show();
    },
    do_hide: function () {
        this.$element.hide();
    },
    do_update_pager: function() {
        var $pager = this.$element.find('div.oe_form_pager');
        $pager.find("button[data-pager-action='first'], button[data-pager-action='previous']").attr('disabled', this.dataset.index == 0);
        $pager.find("button[data-pager-action='next'], button[data-pager-action='last']").attr('disabled', this.dataset.index == this.dataset.ids.length - 1);
        this.$element.find('span.oe_pager_index').html(this.dataset.index + 1);
        this.$element.find('span.oe_pager_count').html(this.dataset.count);
    },
    on_pager_action: function(action) {
        switch (action) {
            case 'first':
                this.dataset.index = 0;
                break;
            case 'previous':
                this.dataset.previous();
                break;
            case 'next':
                this.dataset.next();
                break;
            case 'last':
                this.dataset.index = this.dataset.ids.length - 1;
                break;
        }
        this.dataset.fetch_index(this.fields_view.fields, this.on_record_loaded);
    },
    on_invalid: function() {
    },
    on_saved: function() {
        // Check response for exceptions, display error
    },
    do_search: function (domains, contexts, groupbys) {
    },
    on_action: function (action) {
    }
});

/** @namespace */
openerp.base.form = {};

openerp.base.form.Widget = openerp.base.Controller.extend({
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

openerp.base.form.WidgetFrame = openerp.base.form.Widget.extend({
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
        var widget = new (openerp.base.form.widgets.get_object(widget_type)) (this.view, n);
        if (n.tag == 'field' && n.attrs.nolabel != '1') {
            var label = new (openerp.base.form.widgets.get_object('label')) (this.view, n);
            label["for"] = widget;
            this.add_widget(label);
        }
        this.add_widget(widget);
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

openerp.base.form.WidgetNotebook = openerp.base.form.Widget.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "WidgetNotebook";
        this.pages = [];
        for (var i = 0; i < node.children.length; i++) {
            var n = node.children[i];
            if (n.tag == "page") {
                var page = new openerp.base.form.WidgetFrame(this.view, n);
                this.pages.push(page);
            }
        }
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element.tabs();
    }
});

openerp.base.form.WidgetSeparator = openerp.base.form.Widget.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "WidgetSeparator";
    }
});

openerp.base.form.WidgetButton = openerp.base.form.Widget.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "WidgetButton";
    }
});

openerp.base.form.WidgetLabel = openerp.base.form.Widget.extend({
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

openerp.base.form.Field = openerp.base.form.Widget.extend({
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

openerp.base.form.FieldChar = openerp.base.form.Field.extend({
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
        var show_value = (value != null && value !== false) ? value : '';
        this.$element.find('input').val(show_value);
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

openerp.base.form.FieldEmail = openerp.base.form.FieldChar.extend({
});

openerp.base.form.FieldUrl = openerp.base.form.FieldChar.extend({
});

openerp.base.form.FieldFloat = openerp.base.form.Field.extend({
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
        var show_value = (value != null && value !== false) ? value.toFixed(2) : '';
        this.$element.find('input').val(value);
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

openerp.base.form.FieldText = openerp.base.form.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldText";
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        var show_value = (value != null && value !== false) ? value : '';
        this.$element.find('textarea').val(show_value);
    },
    get_value: function() {
        return this.$element.find('textarea').val();
    }
});

openerp.base.form.FieldBoolean = openerp.base.form.Field.extend({
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

openerp.base.form.FieldDate = openerp.base.form.FieldChar.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldDate";
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element.find('input').datepicker({
            dateFormat: 'yy-mm-dd'
        });
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        var show_value = (value != null && value !== false) ? value : '';
        this.$element.find('input').val(show_value);
    },
    get_value: function() {
    }
});

openerp.base.form.FieldDatetime = openerp.base.form.FieldChar.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldDatetime";
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element.find('input').datetimepicker({
            dateFormat: 'yy-mm-dd',
            timeFormat: 'hh:mm:ss'
        });
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        var show_value = (value != null && value !== false) ? value : '';
        this.$element.find('input').val(show_value);
    },
    get_value: function() {
    }
});

openerp.base.form.FieldTextXml = openerp.base.form.Field.extend({
// to replace view editor
});

openerp.base.form.FieldSelection = openerp.base.form.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldSelection";
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        if (value != null && value !== false) {
            this.$element.find('select').val(value);
        } else {
            this.$element.find('select')[0].selectedIndex = 0;
        }
    },
    get_value: function() {
        return this.$element.find('select').val();
    }
});

openerp.base.form.FieldMany2One = openerp.base.form.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldMany2One";
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        var show_value = (value != null && value !== false) ? value[1] : '';
        this.$element.find('input').val(show_value);
    }
});

openerp.base.form.FieldOne2Many = openerp.base.form.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldOne2Many";
        this.viewmanager = null;
        this.operations = [];
        // thise.iewq.on

    },
    set_value: function(value) {
        this.value = value;
    },
    get_value: function(value) {
        return this.operations;
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

openerp.base.form.FieldMany2Many = openerp.base.form.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldMany2Many";
    }
});

openerp.base.form.FieldReference = openerp.base.form.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldReference";
    }
});

/**
 * Registry of form widgets, called by :js:`openerp.base.FormView`
 */
openerp.base.form.widgets = new openerp.base.Registry({
    'group' : 'openerp.base.form.WidgetFrame',
    'notebook' : 'openerp.base.form.WidgetNotebook',
    'separator' : 'openerp.base.form.WidgetSeparator',
    'label' : 'openerp.base.form.WidgetLabel',
    'button' : 'openerp.base.form.WidgetButton',
    'char' : 'openerp.base.form.FieldChar',
    'email' : 'openerp.base.form.FieldEmail',
    'url' : 'openerp.base.form.FieldUrl',
    'text' : 'openerp.base.form.FieldText',
    'date' : 'openerp.base.form.FieldDate',
    'datetime' : 'openerp.base.form.FieldDatetime',
    'selection' : 'openerp.base.form.FieldSelection',
    'many2one' : 'openerp.base.form.FieldMany2One',
    'many2many' : 'openerp.base.form.FieldMany2Many',
    'one2many' : 'openerp.base.form.FieldOne2Many',
    'one2many_list' : 'openerp.base.form.FieldOne2Many',
    'reference' : 'openerp.base.form.FieldReference',
    'boolean' : 'openerp.base.form.FieldBoolean',
    'float' : 'openerp.base.form.FieldFloat'
});

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
