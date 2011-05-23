
openerp.base.form = function (openerp) {

openerp.base.views.add('form', 'openerp.base.FormView');
openerp.base.FormView =  openerp.base.View.extend( /** @lends openerp.base.FormView# */{
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
        this.show_invalid = true;
        this.touched = false;
        this.flags = view_manager.action.flags || {};
    },
    start: function() {
        //this.log('Starting FormView '+this.model+this.view_id)
        return this.rpc("/base/formview/load", {"model": this.model, "view_id": this.view_id,
            toolbar:!!this.view_manager.sidebar}, this.on_loaded);
    },
    on_loaded: function(data) {
        var self = this;
        this.fields_view = data.fields_view;

        var frame = new openerp.base.form.WidgetFrame(this, this.fields_view.arch);

        this.$element.html(QWeb.render("FormView", { 'frame': frame, 'view': this }));
        _.each(this.widgets, function(w) {
            w.start();
        });
        this.$element.find('div.oe_form_pager button[data-pager-action]').click(function() {
            var action = $(this).data('pager-action');
            self.on_pager_action(action);
        });

        this.$element.find('#' + this.element_id + '_header button.oe_form_button_save').click(this.do_save);
        this.$element.find('#' + this.element_id + '_header button.oe_form_button_save_edit').click(this.do_save_edit);
        this.$element.find('#' + this.element_id + '_header button.oe_form_button_cancel').click(this.do_cancel);
        this.$element.find('#' + this.element_id + '_header button.oe_form_button_new').click(this.on_button_new);

        // sidebar stuff
        if (this.view_manager.sidebar) {
            this.view_manager.sidebar.set_toolbar(data.fields_view.toolbar);
        }
    },
    do_show: function () {
        var self = this;
        this.do_update_pager.add(function() {
            self.$element.show();
        });
        if (this.dataset.index === null) {
            // null index means we should start a new record
            this.on_button_new();
        } else {
            this.dataset.read_index(_.keys(this.fields_view.fields), this.on_record_loaded);
        }
        if (this.view_manager && this.view_manager.sidebar) {
            this.view_manager.sidebar.refresh(true);
        }
    },
    do_hide: function () {
        this.$element.hide();
    },
    on_record_loaded: function(record) {
        this.touched = false;
        if (record) {
            this.datarecord = record;
            for (var f in this.fields) {
                var field = this.fields[f];
                field.set_value(this.datarecord[f] || false);
                field.validate();
                field.touched = false;
            }
            if (!record.id) {
                // New record: Second pass in order to trigger the onchanges
                this.touched = true;
                this.show_invalid = false;
                for (var f in record) {
                    this.on_form_changed(this.fields[f]);
                }
            }
            this.on_form_changed();
            this.show_invalid = this.ready = true;
        } else {
            this.log("No record received");
        }
        this.do_update_pager(record.id == null);
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
        this.reload();
    },
    do_update_pager: function(hide_index) {
        var $pager = this.$element.find('#' + this.element_id + '_header div.oe_form_pager');
        var index = hide_index ? '-' : this.dataset.index + 1;
        $pager.find('span.oe_pager_index').html(index);
        $pager.find('span.oe_pager_count').html(this.dataset.count);
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
                var argument_replacement = {
                    'False' : false,
                    'True' : true,
                    'None' : null
                }
                _.each(call[2].split(','), function(a) {
                    var field = _.trim(a);
                    if (field in argument_replacement) {
                        args.push(argument_replacement[field]);
                    } else if (self.fields[field]) {
                        var value = self.fields[field].value;
                        args.push(value == null ? false : value);
                    } else {
                        args.push(false);
                        self.log("warning : on_change can't find field " + field, onchange);
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
    do_save: function(success) {
        var self = this;
        if (!this.ready) {
            return false;
        }
        var invalid = false;
        var values = {};
        for (var f in this.fields) {
            f = this.fields[f];
            if (f.invalid) {
                invalid = true;
                f.update_dom();
            } else if (f.touched) {
                values[f.name] = f.get_value();
            }
        }
        if (invalid) {
            this.on_invalid();
            return false;
        } else {
            this.log("About to save", values);
            if (!this.datarecord.id) {
                this.dataset.create(values, function(r) {
                    self.on_created(r, success);
                });
            } else {
                this.dataset.write(this.datarecord.id, values, function(r) {
                    self.on_saved(r, success);
                });
            }
            return true;
        }
    },
    do_save_edit: function() {
        this.do_save();
        //this.switch_readonly(); Use promises
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
        this.notification.warn("The following fields are invalid :", msg);
    },
    on_saved: function(r, success) {
        if (!r.result) {
            this.notification.warn("Record not saved", "Problem while saving record.");
        } else {
            this.notification.notify("Record saved", "The record #" + this.datarecord.id + " has been saved.");
            if (success) {
                success(r);
            }
        }
    },
    on_created: function(r, success) {
        if (!r.result) {
            this.notification.warn("Record not created", "Problem while creating record.");
        } else {
            this.datarecord.id = arguments[0].result;
            this.dataset.ids.push(this.datarecord.id);
            this.dataset.index = this.dataset.ids.length - 1;
            this.dataset.count++;
            this.do_update_pager();
            this.notification.notify("Record created", "The record has been created with id #" + this.datarecord.id);
            if (success) {
                success(r);
            }
        }
    },
    do_search: function (domains, contexts, groupbys) {
        this.notification.notify("Searching form");
    },
    on_action: function (action) {
        this.notification.notify('Executing action ' + action);
    },
    do_cancel: function () {
        this.notification.notify("Cancelling form");
    },
    reload: function() {
        if (this.datarecord.id) {
            this.dataset.read_index(_.keys(this.fields_view.fields), this.on_record_loaded);
        } else {
            this.on_button_new();
        }
    }
});

/** @namespace */
openerp.base.form = {};

openerp.base.form.compute_domain = function(expr, fields) {
    var stack = [];
    for (var i = expr.length - 1; i >= 0; i--) {
        var ex = expr[i];
        if (ex.length == 1) {
            var top = stack.pop();
            switch (ex) {
                case '|':
                    stack.push(stack.pop() || top);
                    continue;
                case '&':
                    stack.push(stack.pop() && top);
                    continue;
                case '!':
                    stack.push(!top);
                    continue;
                default:
                    throw new Error('Unknown domain operator ' + ex);
            }
        }

        var field = fields[ex[0]].value;
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
                stack.push(_(val).contains(field));
                break;
            case 'not in':
                stack.push(!_(val).contains(field));
                break;
            default:
                this.log("Unsupported operator in attrs :", op);
        }
    }
    return _.all(stack);
};

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
        var compute_domain = openerp.base.form.compute_domain;
        for (var a in this.attrs) {
            this[a] = compute_domain(this.attrs[a], this.view.fields);
        }
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
    handle_node: function(node) {
        var type = this.view.fields_view.fields[node.attrs.name] || {};
        var widget_type = node.attrs.widget || type.type || node.tag;
        var widget = new (openerp.base.form.widgets.get_object(widget_type)) (this.view, node);
        if (node.tag == 'field' && node.attrs.nolabel != '1') {
            var label = new (openerp.base.form.widgets.get_object('label')) (this.view, node);
            label["for"] = widget;
            this.add_widget(label);
        }
        this.add_widget(widget);
    },
    add_widget: function(widget) {
        var current_row = this.table[this.table.length - 1];
        if (current_row.length && (this.x + widget.colspan) > this.columns) {
            current_row = this.add_row();
        }
        current_row.push(widget);
        this.x += widget.colspan;
        return widget;
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
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element.click(this.on_click);
    },
    on_click: function(saved) {
        var self = this;
        if (!this.node.attrs.special && this.view.touched && saved !== true) {
            this.view.do_save(function() {
                self.on_click(true);
            });
        } else {
            if (this.node.attrs.confirm) {
                var dialog = $('<div>' + this.node.attrs.confirm + '</div>').dialog({
                    title: 'Confirm',
                    modal: true,
                    buttons: {
                        Ok: function() {
                            self.on_confirmed();
                            $(this).dialog("close");
                        },
                        Cancel: function() {
                            $(this).dialog("close");
                        }
                    }
                });
            } else {
                this.on_confirmed();
            }
        }
    },
    on_confirmed: function() {
        var self = this;

        this.view.execute_action(
            this.node.attrs, this.view.dataset, this.session.action_manager,
            this.view.datarecord.id, function (result) {
                self.log("Button returned", result);
                self.view.reload();
            });
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
        this.field = view.fields_view.fields[node.attrs.name] || {};
        this.string = node.attrs.string || this.field.string;
        this.help = node.attrs.help || this.field.help;
        this.invisible = (this.invisible || this.field.invisible == '1');
        this.nolabel = (this.field.nolabel || node.attrs.nolabel) == '1';
        this.readonly = (this.field.readonly || node.attrs.readonly) == '1';
        this.required = (this.field.required || node.attrs.required) == '1';
        this.invalid = false;
        this.touched = false;
    },
    set_value: function(value) {
        this.value = value;
        this.invalid = false;
        this.update_dom();
    },
    set_value_from_ui: function() {
        this.value = undefined;
    },
    get_value: function() {
        return this.value;
    },
    update_dom: function() {
        this._super.apply(this, arguments);
        this.$element.toggleClass('disabled', this.readonly);
        this.$element.toggleClass('required', this.required);
        if (this.view.show_invalid) {
            this.$element.toggleClass('invalid', this.invalid);
        }
    },
    on_ui_change: function() {
        this.touched = this.view.touched = true;
        this.set_value_from_ui();
        this.validate();
        this.view.on_form_changed(this);
    },
    validate: function() {
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
    set_value_from_ui: function() {
        this.value = this.$element.find('input').val();
    },
    validate: function() {
        this.invalid = false;
        if (this.value === false || this.value === "") {
            this.invalid = this.required;
        } else if (this.validation_regex) {
            this.invalid = !this.validation_regex.test(this.value);
        }
    }
});

openerp.base.form.FieldEmail = openerp.base.form.FieldChar.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldEmail";
        this.validation_regex = /@/;
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element.find('button').click(this.on_button_clicked);
    },
    on_button_clicked: function() {
        if (!this.value || this.invalid) {
            this.notification.warn("E-mail error", "Can't send email to invalid e-mail address");
        } else {
            location.href = 'mailto:' + this.value;
        }
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        var show_value = (value != null && value !== false) ? value : '';
        this.$element.find('a').attr('href', 'mailto:' + show_value);
    }
});

openerp.base.form.FieldUrl = openerp.base.form.FieldChar.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldUrl";
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element.find('button').click(this.on_button_clicked);
    },
    on_button_clicked: function() {
        if (!this.value) {
            this.notification.warn("Resource error", "This resource is empty");
        } else {
            window.open(this.value);
        }
    }
});

openerp.base.form.FieldFloat = openerp.base.form.FieldChar.extend({
    init: function(view, node) {
        this._super(view, node);
        this.validation_regex = /^-?\d+(\.\d+)?$/;
    },
    set_value: function(value) {
        if (!value) {
            // As in GTK client, floats default to 0
            value = 0;
        }
        this._super.apply(this, [value]);
        var show_value = value.toFixed(2);
        this.$element.find('input').val(show_value);
    },
    set_value_from_ui: function() {
        this.value = this.$element.find('input').val().replace(/,/g, '.');
    },
    validate: function() {
        this._super.apply(this, arguments);
        if (!this.invalid) {
            this.value = Number(this.value);
        }
    }
});

openerp.base.form.FieldDatetime = openerp.base.form.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldDate";
        this.jqueryui_object = 'datetimepicker';
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element.find('input').change(this.on_ui_change)[this.jqueryui_object]({
            dateFormat: 'yy-mm-dd',
            timeFormat: 'hh:mm:ss'
        });
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        if (value == null || value == false) {
            this.$element.find('input').val('');
        } else {
            this.value = this.parse(value);
            this.$element.find('input')[this.jqueryui_object]('setDate', this.value);
        }
    },
    set_value_from_ui: function() {
        this.value = this.$element.find('input')[this.jqueryui_object]('getDate') || false;
        if (this.value) {
            this.value = this.format(this.value);
        }
    },
    validate: function() {
        this.invalid = this.required && this.value === false;
    },
    parse: openerp.base.parse_datetime,
    format: openerp.base.format_datetime
});

openerp.base.form.FieldDate = openerp.base.form.FieldDatetime.extend({
    init: function(view, node) {
        this._super(view, node);
        this.jqueryui_object = 'datepicker';
    },
    parse: openerp.base.parse_date,
    format: openerp.base.format_date
});

openerp.base.form.FieldFloatTime = openerp.base.form.FieldChar.extend({
    init: function(view, node) {
        this._super(view, node);
        this.validation_regex = /^\d+:\d+$/;
    },
    set_value: function(value) {
        value = value || 0;
        this._super.apply(this, [value]);
        var show_value = _.sprintf("%02d:%02d", Math.floor(value), Math.round((value % 1) * 60));
        this.$element.find('input').val(show_value);
    },
    validate: function() {
        if (typeof(this.value) == "string") {
            this._super.apply(this, arguments);
            if (!this.invalid) {
                var time = this.value.split(':');
                this.set_value(parseInt(time[0], 10) + parseInt(time[1], 10) / 60);
            }
        }
    }
});

openerp.base.form.FieldText = openerp.base.form.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldText";
        this.validation_regex = null;
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
    set_value_from_ui: function() {
        this.value = this.$element.find('textarea').val();
    },
    validate: function() {
        this.invalid = false;
        if (this.value === false || this.value === "") {
            this.invalid = this.required;
        } else if (this.validation_regex) {
            this.invalid = !this.validation_regex.test(this.value);
        }
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
    set_value_from_ui: function() {
        this.value = this.$element.find('input').is(':checked');
    },
    update_dom: function() {
        this._super.apply(this, arguments);
        this.$element.find('input').attr('disabled', this.readonly);
    },
    validate: function() {
        this.invalid = this.required && !this.value;
    }
});

openerp.base.form.FieldProgressBar = openerp.base.form.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldProgressBar";
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element.find('div').progressbar({
            value: this.value,
            disabled: this.readonly
        });
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        var show_value = Number(value);
        if (show_value === NaN) {
            show_value = 0;
        }
        this.$element.find('div').progressbar('option', 'value', show_value).find('span').html(show_value + '%');
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
    set_value_from_ui: function() {
        this.value = this.$element.find('select').val();
    },
    update_dom: function() {
        this._super.apply(this, arguments);
        this.$element.find('select').attr('disabled', this.readonly);
    },
    validate: function() {
        this.invalid = this.required && this.value === "";
    }
});

openerp.base.form.FieldMany2OneDatasSet = openerp.base.DataSetStatic.extend({
    start: function() {
    },
    write: function (id, data, callback) {
        this._super(id, data, callback);
    }
});

openerp.base.form.FieldMany2OneViewManager = openerp.base.ViewManager.extend({
    init: function(session, element_id, dataset, views) {
        this._super(session, element_id, dataset, views);
    }
});

openerp.base.form.FieldMany2One = openerp.base.form.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldMany2One";
        this.is_field_m2o = true;
    },
    start: function() {
        this.$element = $('#' + this.element_id);
        this.dataset = new openerp.base.form.FieldMany2OneDatasSet(this.session, this.field.relation);
        var views = [ [false,"list"], [false,"form"] ];
        this.viewmanager = new openerp.base.form.FieldMany2OneViewManager(this.view.session, this.element_id, this.dataset, views);
        new openerp.base.m2o(this.viewmanager, this.$element, this.field.relation, this.dataset, this.session)
        this.$element.find('input').change(this.on_ui_change);
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        var show_value = '';
        if (value != null && value !== false) {
            show_value = value[1];
            this.value = value[0];
        }
        this.$element.find('input').val(show_value);
        this.$element.find('input').attr('m2o_id', this.value);
    },

    get_value: function() {
        var val = this.$element.find('input').attr('m2o_id') || this.value
        return val;
    },

    on_ui_change: function() {
        this.touched = this.view.touched = true;
    }
});

openerp.base.form.FieldOne2ManyDatasSet = openerp.base.DataSetStatic.extend({
    start: function() {
    },
    write: function (id, data, callback) {
        this._super(id, data, callback);
    },
    unlink: function() {
        this.notification.notify('Unlinking o2m ' + this.ids);
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
    set_value: function(value) {
        this.value = value;
        if (value != false) {
            this.log("o2m.set_value",value);
            this.viewmanager.dataset.ids = value;
            this.viewmanager.dataset.count = value.length;
            this.viewmanager.views.list.controller.do_update();
        }
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
        this.list_id = _.uniqueId("many2many");
        this.is_started = false;
        this.is_setted = false;
    },
    start: function() {
        this._super.apply(this, arguments);
        this.dataset = new openerp.base.DataSetMany2Many(this.session, this.field.relation);
        this.list_view = new openerp.base.form.Many2ManyListView(undefined, this.view.session,
                this.list_id, this.dataset, false, {'selected': false, 'addable': 'Add'});
        var self = this;
        this.list_view.m2m_field = this;
        this.list_view.start();
        var hack = {loaded: false};
        this.list_view.on_loaded.add_last(function() {
            if (! hack.loaded) {
                self.is_started = true;
                self.check_load();
                hack.loaded = true;
            }
        });
    },
    set_value: function(value) {
        if (value != false) {
            this.dataset.ids = value;
            this.dataset.count = value.length;
            this.is_setted = true;
            this.check_load();
        }
    },
    get_value: function() {
        return [[6,false,this.dataset.ids]];
    },
    check_load: function() {
        if(this.is_started && this.is_setted) {
            this.list_view.do_reload();
        }
    }
});

openerp.base.form.Many2ManyListView = openerp.base.ListView.extend({
    do_delete: function (ids) {
        this.dataset.ids = _.without.apply(null, [this.dataset.ids].concat(ids));
        this.dataset.count = this.dataset.ids.length;
        // there may be a faster way
        this.do_reload();
        
        this.m2m_field.on_ui_change();
    },
    do_reload: function () {
        /* Dear xmo, according to your comments, this method's implementation in list view seems
         * to be a little bit bullshit.
         * I assume the list view will be changed later, so I hope it will support static datasets.
         */
        return this.rpc('/base/listview/fill', {
            'model': this.dataset.model,
            'id': this.view_id,
            'domain': [["id", "in", this.dataset.ids]],
            'context': this.dataset.context
        }, this.do_fill_table);
    },
    do_add_record: function (e) {
        e.stopImmediatePropagation();
        var pop = new openerp.base.form.Many2XSelectPopup(null, this.m2m_field.view.session);
        pop.select_element(this.model);
        var self = this;
        pop.on_select_element.add(function(element_id) {
            if(! _.detect(self.dataset.ids, function(x) {return x == element_id;})) {
                self.dataset.ids.push(element_id);
                self.dataset.count = self.dataset.ids.length;
                self.do_reload();
            }
            pop.stop();
        });
    },
    select_record: function(index) {
        var id = this.rows[index].data.id.value;
        if(! id) {
            return;
        }
        var action_manager = this.m2m_field.view.session.action_manager;
        action_manager.do_action({
            "res_model": this.dataset.model,
            "views":[[false,"form"]],
            "res_id": id,
            "type":"ir.actions.act_window",
            "view_type":"form",
            "view_mode":"form",
            "target":"new"
        });
    }
});

openerp.base.form.Many2XSelectPopup = openerp.base.BaseWidget.extend({
    identifier_prefix: "many2xselectpopup",
    template: "Many2XSelectPopup",
    select_element: function(model, dataset) {
        this.model = model;
        this.dataset = dataset
        var html = this.render();
        jQuery(html).dialog({title: '',
                    modal: true,
                    minWidth: 800});
        this.start();
    },
    start: function() {
        this._super();
        if (!this.dataset) {
            this.dataset = new openerp.base.DataSetSearch(this.session, this.model);
        }
        this.setup_search_view();
    },
    setup_search_view: function() {
        var self = this;
        if (this.searchview) {
            this.searchview.stop();
        }
        this.searchview = new openerp.base.SearchView(this, this.session, this.element_id + "_search",
                this.dataset, false, {});
        this.searchview.on_search.add(function(domains, contexts, groupbys) {
            self.view_list.do_search.call(
                self, domains, contexts, groupbys);
        });
        this.searchview.on_loaded.add_last(function () {
            var $buttons = self.searchview.$element.find(".oe_search-view-buttons");
            $buttons.append(QWeb.render("Many2XSelectPopup.search.buttons"));
            var $nbutton = $buttons.find(".oe_many2xselectpopup-search-new");
            $nbutton.click(function() {
                self.new_object();
            });
            var $cbutton = $buttons.find(".oe_many2xselectpopup-search-close");
            $cbutton.click(function() {
                self.stop();
            });
            self.view_list = new openerp.base.form.Many2XPopupListView( null, self.session,
                    self.element_id + "_view_list", self.dataset, false);
            self.view_list.popup = self;
            self.view_list.do_show();
            self.view_list.start();
            var tmphack = {"loaded": false};
            self.view_list.on_loaded.add_last(function() {
                if ( !tmphack.loaded ) {
                    self.view_list.do_reload();
                    tmphack.loaded = true;
                };
            });
        });
        this.searchview.start();
    },
    on_select_element: function(element_id) {
    },
    new_object: function() {
        var self = this;
        this.searchview.hide();
        this.view_list.$element.hide();
        this.dataset.index = null;
        this.view_form = new openerp.base.FormView({}, this.session,
                this.element_id + "_view_form", this.dataset, false);
        this.view_form.start();
        this.view_form.on_loaded.add_last(function() {
            var $buttons = self.view_form.$element.find(".oe_form_buttons");
            $buttons.html(QWeb.render("Many2XSelectPopup.form.buttons"));
            var $nbutton = $buttons.find(".oe_many2xselectpopup-form-save");
            $nbutton.click(function() {
                self.view_form.do_save();
            });
            var $cbutton = $buttons.find(".oe_many2xselectpopup-form-close");
            $cbutton.click(function() {
                self.stop();
            });
        });
        this.view_form.on_created.add_last(function(r, success) {
            if (r.result) {
                var id = arguments[0].result;
                self.on_select_element(id);
            }
        });
        this.view_form.do_show();
    }
});

openerp.base.form.Many2XPopupListView = openerp.base.ListView.extend({
    switch_to_record: function(index) {
        this.popup.on_select_element(this.dataset.ids[index]);
    }
});

openerp.base.form.FieldReference = openerp.base.form.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldReference";
    }
});

openerp.base.form.FieldBinary = openerp.base.form.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.iframe = this.element_id + '_iframe';
        this.binary_value = false;
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element.find('input.oe-binary-file').change(this.on_file_change);
        this.$element.find('button.oe-binary-file-save').click(this.on_save_as);
        this.$element.find('.oe-binary-file-clear').click(this.on_clear);
    },
    set_value_from_ui: function() {
    },
    human_filesize : function(size) {
        var units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
        var i = 0;
        while (size >= 1024) {
            size /= 1024;
            ++i;
        }
        return size.toFixed(2) + ' ' + units[i];
    },
    on_file_change: function(e) {
        // TODO: on modern browsers, we could directly read the file locally on client ready to be used on image cropper
        // http://www.html5rocks.com/tutorials/file/dndfiles/
        // http://deepliquid.com/projects/Jcrop/demos.php?demo=handler
        window[this.iframe] = this.on_file_uploaded;
        if ($(e.target).val() != '') {
            this.$element.find('form.oe-binary-form input[name=session_id]').val(this.session.session_id);
            this.$element.find('form.oe-binary-form').submit();
            this.toggle_progress();
        }
    },
    toggle_progress: function() {
        this.$element.find('.oe-binary-progress, .oe-binary').toggle();
    },
    on_file_uploaded: function(size, name, content_type, file_base64) {
        delete(window[this.iframe]);
        if (size === false) {
            this.notification.warn("File Upload", "There was a problem while uploading your file");
            // TODO: use openerp web exception handler
            console.log("Error while uploading file : ", name);
        } else {
            this.on_file_uploaded_and_valid.apply(this, arguments);
            this.on_ui_change();
        }
        this.toggle_progress();
    },
    on_file_uploaded_and_valid: function(size, name, content_type, file_base64) {
    },
    on_save_as: function() {
        var url = '/base/binary/saveas?session_id=' + this.session.session_id + '&model=' +
            this.view.dataset.model +'&id=' + (this.view.datarecord.id || '') + '&field=' + this.name +
            '&fieldname=' + (this.node.attrs.filename || '') + '&t=' + (new Date().getTime())
        window.open(url);
    },
    on_clear: function() {
        if (this.value !== false) {
            this.value = false;
            this.binary_value = false;
            this.on_ui_change();
        }
        return false;
    }
});

openerp.base.form.FieldBinaryFile = openerp.base.form.FieldBinary.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldBinaryFile";
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        var show_value = (value != null && value !== false) ? value : '';
        this.$element.find('input').eq(0).val(show_value);
    },
    on_file_uploaded_and_valid: function(size, name, content_type, file_base64) {
        this.value = file_base64;
        this.binary_value = true;
        var show_value = this.human_filesize(size);
        this.$element.find('input').eq(0).val(show_value);
        this.set_filename(name);
    },
    set_filename: function(value) {
        var filename = this.node.attrs.filename;
        if (this.view.fields[filename]) {
            this.view.fields[filename].set_value(value);
            this.view.fields[filename].on_ui_change();
        }
    },
    on_clear: function() {
        this._super.apply(this, arguments);
        this.$element.find('input').eq(0).val('');
        this.set_filename('');
    }
});

openerp.base.form.FieldBinaryImage = openerp.base.form.FieldBinary.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldBinaryImage";
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$image = this.$element.find('img.oe-binary-image');
    },
    set_image_maxwidth: function() {
        this.$image.css('max-width', this.$element.width());
    },
    on_file_change: function() {
        this.set_image_maxwidth();
        this._super.apply(this, arguments);
    },
    on_file_uploaded_and_valid: function(size, name, content_type, file_base64) {
        this.value = file_base64;
        this.binary_value = true;
        this.$image.attr('src', 'data:' + (content_type || 'image/png') + ';base64,' + file_base64);
    },
    on_clear: function() {
        this._super.apply(this, arguments);
        this.$image.attr('src', '/base/static/src/img/placeholder.png');
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        this.set_image_maxwidth();
        var url = '/base/binary/image?session_id=' + this.session.session_id + '&model=' +
            this.view.dataset.model +'&id=' + (this.view.datarecord.id || '') + '&field=' + this.name + '&t=' + (new Date().getTime())
        this.$image.attr('src', url);
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
    'text_wiki' : 'openerp.base.form.FieldText',
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
    'progressbar': 'openerp.base.form.FieldProgressBar',
    'float_time': 'openerp.base.form.FieldFloatTime',
    'image': 'openerp.base.form.FieldBinaryImage',
    'binary': 'openerp.base.form.FieldBinaryFile'
});

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
