
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
    init: function(view_manager, session, element_id, dataset, view_id) {
        this._super(session, element_id);
        this.view_manager = view_manager;
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

        this.$element.find('div.oe_form_buttons button.oe_form_button_save').click(this.do_save);
        this.$element.find('div.oe_form_buttons button.oe_form_button_save_edit').click(this.do_save_edit);
        this.$element.find('div.oe_form_buttons button.oe_form_button_cancel').click(this.do_cancel);
        this.$element.find('div.oe_form_buttons button.oe_form_button_new').click(this.on_button_new);

        // sidebar stuff
        if (this.view_manager.sidebar) {
            this.view_manager.sidebar.load_multi_actions();
        }
    },
    do_show: function () {
        this.dataset.read_index(_.keys(this.fields_view.fields), this.on_record_loaded);
        this.$element.show();
    },
    do_hide: function () {
        this.$element.hide();
    },
    on_record_loaded: function(record) {
        if (record) {
            this.datarecord = record;
            for (var f in this.fields) {
                this.fields[f].set_value(this.datarecord[f]);
            }
            if (!record.id) {
                // Second pass in order to trigger the onchanges in case of new record
                for (var f in record) {
                    this.fields[f].on_ui_change();
                }
            }
            this.on_form_changed();
            this.ready = true;
        } else {
            this.log("No record received");
        }
        this.do_update_pager();
    },
    on_form_changed: function(widget) {
        if (widget && widget.node.attrs.on_change) {
            this.do_onchange(widget);
        } else {
            for (var w in this.widgets) {
                w = this.widgets[w];
                w.process_attrs();
                w.update_dom();
            }
        }
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
        this.dataset.read_index(_.keys(this.fields_view.fields), this.on_record_loaded);
    },
    do_update_pager: function() {
        var $pager = this.$element.find('div.oe_form_pager');
        $pager.find("button[data-pager-action='first'], button[data-pager-action='previous']").attr('disabled', this.dataset.index == 0);
        $pager.find("button[data-pager-action='next'], button[data-pager-action='last']").attr('disabled', this.dataset.index == this.dataset.ids.length - 1);
        this.$element.find('span.oe_pager_index').html(this.dataset.index + 1);
        this.$element.find('span.oe_pager_count').html(this.dataset.count);
    },
    do_onchange: function(widget, processed) {
        processed = processed || [];
        if (widget.node.attrs.on_change) {
            var self = this;
            this.ready = false;
            var onchange = _.trim(widget.node.attrs.on_change);
            var call = onchange.match(/^\s?(.*?)\((.*?)\)\s?$/);
            if (call) {
                var method = call[1], args = [];
                _.each(call[2].split(','), function(a) {
                    var field = _.trim(a);
                    if (self.fields[field]) {
                        var value = self.fields[field].value;
                        args.push(value == null ? false : value);
                    } else {
                        args.push(false);
                        this.log("warning : on_change can't find field " + field, onchange);
                    }
                });
                var ajax = {
                    url: '/base/dataset/call',
                    async: false
                };
                return this.rpc(ajax, {
                    model: this.dataset.model,
                    method: method,
                    ids: (this.datarecord.id == null ? [] : [this.datarecord.id]),
                    args: args
                }, function(response) {
                    self.on_processed_onchange(response, processed);
                });
            } else {
                this.log("Wrong on_change format", on_change);
            }
        }
    },
    on_processed_onchange: function(response, processed) {
        var result = response.result;
        if (result.value) {
            for (var f in result.value) {
                var field = this.fields[f];
                if (field) {
                    var value = result.value[f];
                    processed.push(field.name);
                    if (field.value != value) {
                        field.set_value(value);
                        if (_.indexOf(processed, field.name) < 0) {
                            this.do_onchange(field, processed);
                        }
                    }
                } else {
                    this.log("warning : on_processed_onchange can't find field " + field, result);
                }
            }
            this.on_form_changed();
        }
        if (result.warning) {
            $(QWeb.render("DialogWarning", result.warning)).dialog({
                modal: true,
                buttons: {
                    Ok: function() {
                        $(this).dialog("close");
                    }
                }
            });
        }
        if (result.domain) {
            // Will be removed ?
        }
        this.ready = true;
    },
    on_button_new: function() {
        var self = this;
        this.dataset.default_get(_.keys(this.fields), function(result) {
            self.on_record_loaded(result.result);
        });
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
            } else if (f.touched) {
                values[f.name] = f.get_value();
            }
        }
        if (invalid) {
            this.on_invalid();
        } else {
            this.log("About to save", values);
            this.dataset.write(this.datarecord.id, values, this.on_saved);
        }
    },
    do_save_edit: function() {
        if (this.do_save()) {
            this.switch_readonly();
        }
    },
    switch_readonly: function() {
    },
    switch_editable: function() {
    },
    on_invalid: function() {
        var msg = "<ul>";
        _.each(this.fields, function(f) {
            if (f.invalid) {
                msg += "<li>" + f.string + "</li>";
            }
        });
        msg += "</ul>";
        this.notification.alert("The following fields are invalid :", msg);
    },
    on_saved: function(r) {
        if (!r.result) {
            this.log("Record was not saved");
        } else {
            // Check response for exceptions, display error
            this.notification['default']("Record saved", "The record #" + this.datarecord.id + " has been saved.");
        }
    },
    do_search: function (domains, contexts, groupbys) {
        this.notification['default']("Searching form");
    },
    on_action: function (action) {
        this.notification['default']('Executing action ' + action);
    },
    do_cancel: function () {
        this.notification['default']("Cancelling form");
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
        this.field = view.fields_view.fields[node.attrs.name];
        this.string = node.attrs.string || this.field.string;
        this.help = node.attrs.help || this.field.help;
        this.nolabel = (node.attrs.nolabel == '1');
        this.readonly = (node.attrs.readonly == '1');
        this.required = (node.attrs.required == '1');
        this.invalid = false;
        this.touched = false;
    },
    set_value: function(value) {
        this.value = value;
        this.invalid = false;
        this.update_dom();
    },
    get_value: function() {
        return this.value;
    },
    update_dom: function() {
        this._super.apply(this, arguments);
        this.$element.toggleClass('disabled', this.readonly);
        this.$element.toggleClass('required', this.required);
        this.$element.toggleClass('invalid', this.invalid);
    },
    on_ui_change: function() {
        this.touched = true;
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
    update_dom: function() {
        this._super.apply(this, arguments);
        this.$element.find('input').attr('disabled', this.readonly);
    },
    on_ui_change: function() {
        this._super.apply(this, arguments);
        this.value = this.$element.find('input').val();
        this.invalid = this.required && this.value == "";
        this.view.on_form_changed(this);
    }
});

openerp.base.form.FieldEmail = openerp.base.form.FieldChar.extend({
});

openerp.base.form.FieldUrl = openerp.base.form.FieldChar.extend({
});

openerp.base.form.FieldFloat = openerp.base.form.FieldChar.extend({
    set_value: function(value) {
        this._super.apply(this, arguments);
        var show_value = (value != null && value !== false) ? value.toFixed(2) : '';
        this.$element.find('input').val(value);
    },
    on_ui_change: function() {
        this._super.apply(this, arguments);
        this.value = this.$element.find('input').val().replace(/,/g, '.');
        this.invalid = (this.required && this.value == "") || !this.value.match(/^\d+(\.\d+)?$/) ;
        this.view.on_form_changed(this);
    }
});

openerp.base.form.FieldDate = openerp.base.form.FieldChar.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldDate";
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element.find('input').change(this.on_ui_change).datepicker({
            dateFormat: 'yy-mm-dd'
        });
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        var show_value = (value != null && value !== false) ? value : '';
        this.$element.find('input').val(show_value);
    },
    on_ui_change: function() {
        this._super.apply(this, arguments);
        this.value = this.$element.find('input').val();
        this.invalid = this.required && this.value == "";
        this.view.on_form_changed(this);
    }
});

openerp.base.form.FieldDatetime = openerp.base.form.FieldChar.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldDatetime";
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element.find('input').change(this.on_ui_change).datetimepicker({
            dateFormat: 'yy-mm-dd',
            timeFormat: 'hh:mm:ss'
        });
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        var show_value = (value != null && value !== false) ? value : '';
        this.$element.find('input').val(show_value);
    },
    on_ui_change: function() {
        this._super.apply(this, arguments);
        this.value = this.$element.find('input').val();
        this.invalid = this.required && this.value == "";
        this.view.on_form_changed(this);
    }
});

openerp.base.form.FieldText = openerp.base.form.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldText";
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element.find('textarea').change(this.on_ui_change);
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        var show_value = (value != null && value !== false) ? value : '';
        this.$element.find('textarea').val(show_value);
    },
    update_dom: function() {
        this._super.apply(this, arguments);
        this.$element.find('textarea').attr('disabled', this.readonly);
    },
    on_ui_change: function() {
        this._super.apply(this, arguments);
        this.value = this.$element.find('textarea').val();
        this.invalid = this.required && this.value == "";
        this.view.on_form_changed(this);
    }
});

openerp.base.form.FieldBoolean = openerp.base.form.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldBoolean";
    },
    start: function() {
        var self = this;
        this._super.apply(this, arguments);
        this.$element.find('input').click(function() {
            if ($(this).is(':checked') != self.value) {
                self.on_ui_change();
            }
        });
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        this.$element.find('input')[0].checked = value;
    },
    update_dom: function() {
        this._super.apply(this, arguments);
        this.$element.find('textarea').attr('disabled', this.readonly);
    },
    on_ui_change: function() {
        this._super.apply(this, arguments);
        this.value = this.$element.find('input').is(':checked');
        this.invalid = this.required && !this.value;
        this.view.on_form_changed(this);
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
    start: function() {
        this._super.apply(this, arguments);
        this.$element.find('select').change(this.on_ui_change);
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        if (value != null && value !== false) {
            this.$element.find('select').val(value);
        } else {
            this.$element.find('select')[0].selectedIndex = 0;
        }
    },
    update_dom: function() {
        this._super.apply(this, arguments);
        this.$element.find('select').attr('disabled', this.readonly);
    },
    on_ui_change: function() {
        this._super.apply(this, arguments);
        this.value = this.$element.find('select').val();
        this.invalid = this.required && this.value == "";
        this.view.on_form_changed(this);
    }
});

openerp.base.form.FieldMany2One = openerp.base.form.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldMany2One";
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        var show_value = '';
        if (value != null && value !== false) {
            show_value = value[1];
            this.value = value[0];
        }
        this.$element.find('input').val(show_value);
    }
});

openerp.base.form.FieldOne2ManyDatasSet = openerp.base.DataSetStatic.extend({
    start: function() {
    },
    write: function (id, data, callback) {
        this._super(id, data, callback);
    },
    unlink: function() {
        this.notification['default']('Unlinking o2m ' + this.ids);
    }
});

openerp.base.form.FieldOne2ManyViewManager = openerp.base.ViewManager.extend({
    init: function(session, element_id, dataset, views) {
        this._super(session, element_id, dataset, views);
    }
});

openerp.base.form.FieldOne2Many = openerp.base.form.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldOne2Many";
        this.operations = [];
    },
    start: function() {
        this._super.apply(this, arguments);
        this.log("o2m.start");
        var views = [ [false,"list"], [false,"form"] ];
        this.dataset = new openerp.base.form.FieldOne2ManyDatasSet(this.session, this.field.relation);
        this.viewmanager = new openerp.base.form.FieldOne2ManyViewManager(this.view.session, this.element_id, this.dataset, views);
        this.viewmanager.start();
    },
    set_value_CASSEEEEEEEEEEEEEEEEE: function(value) {
        this.value = value;
        this.log("o2m.set_value",value);
        this.viewmanager.dataset.ids = value;
        this.viewmanager.dataset.ids.count = value.length;
        this.viewmanager.views.list.controller.do_update();
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
    'float' : 'openerp.base.form.FieldFloat',
    'integer': 'openerp.base.form.FieldFloat',
    'progressbar': 'openerp.base.form.FieldFloat',
    'float_time': 'openerp.base.form.FieldFloat'
});

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
