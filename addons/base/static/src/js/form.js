openerp.base.form = function (openerp) {

var _t = openerp.base._t;

openerp.base.views.add('form', 'openerp.base.FormView');
openerp.base.FormView = openerp.base.View.extend( /** @lends openerp.base.FormView# */{
    /**
     * Indicates that this view is not searchable, and thus that no search
     * view should be displayed (if there is one active).
     */
    searchable: false,
    template: "FormView",
    /**
     * @constructs
     * @param {openerp.base.Session} session the current openerp session
     * @param {String} element_id this view's root element id
     * @param {openerp.base.DataSet} dataset the dataset this view will work with
     * @param {String} view_id the identifier of the OpenERP view object
     *
     * @property {openerp.base.Registry} registry=openerp.base.form.widgets widgets registry for this form view instance
     */
    init: function(parent, element_id, dataset, view_id, options) {
        this._super(parent, element_id);
        this.set_default_options(options);
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
        this.dirty = false;
        this.default_focus_field = null;
        this.default_focus_button = null;
        this.registry = openerp.base.form.widgets;
        this.has_been_loaded = $.Deferred();
        this.$form_header = null;
        _.defaults(this.options, {"always_show_new_button": true});
    },
    start: function() {
        //this.log('Starting FormView '+this.model+this.view_id)
        if (this.embedded_view) {
            var def = $.Deferred().then(this.on_loaded);
            var self = this;
            setTimeout(function() {def.resolve({fields_view: self.embedded_view});}, 0);
            return def.promise();
        } else {
            var context = new openerp.base.CompoundContext(this.dataset.get_context());
            return this.rpc("/base/formview/load", {"model": this.model, "view_id": this.view_id,
                toolbar: this.options.sidebar, context: context}, this.on_loaded);
        }
    },
    stop: function() {
        if (this.sidebar) {
            this.sidebar.attachments.stop();
            this.sidebar.stop();
        }
        _.each(this.widgets, function(w) {
            w.stop();
        });
    },
    on_loaded: function(data) {
        var self = this;
        this.fields_view = data.fields_view;
        var frame = new (this.registry.get_object('frame'))(this, this.fields_view.arch);

        this.$element.html(QWeb.render(this.template, { 'frame': frame, 'view': this }));
        _.each(this.widgets, function(w) {
            w.start();
        });
        this.$form_header = this.$element.find('#' + this.element_id + '_header');
        this.$form_header.find('div.oe_form_pager button[data-pager-action]').click(function() {
            var action = $(this).data('pager-action');
            self.on_pager_action(action);
        });

        this.$form_header.find('button.oe_form_button_save').click(this.do_save);
        this.$form_header.find('button.oe_form_button_save_edit').click(this.do_save_edit);
        this.$form_header.find('button.oe_form_button_cancel').click(this.do_cancel);
        this.$form_header.find('button.oe_form_button_new').click(this.on_button_new);

        this.$form_header.find('button.oe_get_xml_view').click(function() {
            $('<xmp>' + openerp.base.json_node_to_xml(self.fields_view.arch, true) + '</xmp>').dialog({ width: '95%', height: 600});
        });

        if (this.options.sidebar && this.options.sidebar_id) {
            this.sidebar = new openerp.base.Sidebar(this, this.options.sidebar_id);
            this.sidebar.start();
            this.sidebar.do_unfold();
            this.sidebar.attachments = new openerp.base.form.SidebarAttachments(this.sidebar, this.sidebar.add_section('attachments', "Attachments"), this);
            this.sidebar.add_toolbar(data.fields_view.toolbar);
            this.set_common_sidebar_sections(this.sidebar);
        }
        this.has_been_loaded.resolve();
    },
    do_show: function () {
        var promise;
        if (this.dataset.index === null) {
            // null index means we should start a new record
            promise = this.on_button_new();
        } else {
            promise = this.dataset.read_index(_.keys(this.fields_view.fields), this.on_record_loaded);
        }
        this.$element.show();
        if (this.sidebar) {
            this.sidebar.$element.show();
        }
        return promise;
    },
    do_hide: function () {
        this.$element.hide();
        if (this.sidebar) {
            this.sidebar.$element.hide();
        }
    },
    on_record_loaded: function(record) {
        if (!record) {
            throw("Form: No record received");
        }
        if (!record.id) {
            this.$form_header.find('.oe_form_on_create').show();
            this.$form_header.find('.oe_form_on_update').hide();
            if (!this.options["always_show_new_button"]) {
                this.$form_header.find('button.oe_form_button_new').hide();
            }
        } else {
            this.$form_header.find('.oe_form_on_create').hide();
            this.$form_header.find('.oe_form_on_update').show();
            this.$form_header.find('button.oe_form_button_new').show();
        }
        this.dirty = false;
        this.datarecord = record;
        for (var f in this.fields) {
            var field = this.fields[f];
            field.dirty = false;
            field.set_value(this.datarecord[f] || false);
            field.validate();
        }
        if (!record.id) {
            // New record: Second pass in order to trigger the onchanges
            this.dirty = true;
            this.show_invalid = false;
            for (var f in record) {
                var field = this.fields[f];
                if (field) {
                    field.dirty = true;
                    this.do_onchange(field);
                }
            }
        }
        this.on_form_changed();
        this.show_invalid = this.ready = true;
        this.do_update_pager(record.id == null);
        if (this.sidebar) {
            this.sidebar.attachments.do_update();
        }
        if (this.default_focus_field && !this.embedded_view) {
            this.default_focus_field.focus();
        }
    },
    on_form_changed: function() {
        for (var w in this.widgets) {
            w = this.widgets[w];
            w.process_modifiers();
            w.update_dom();
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
        $pager.find('span.oe_pager_count').html(this.dataset.ids.length);
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
                var context_index = null;
                var argument_replacement = {
                    'False' : function() {return false;},
                    'True' : function() {return true;},
                    'None' : function() {return null;},
                    'context': function(i) {
                        context_index = i;
                        var ctx = widget.build_context ? widget.build_context() : {};
                        return ctx;
                    }
                }
                var parent_fields = null;
                _.each(call[2].split(','), function(a, i) {
                    var field = _.trim(a);
                    if (field in argument_replacement) {
                        args.push(argument_replacement[field](i));
                        return;
                    } else if (self.fields[field]) {
                        var value = self.fields[field].get_on_change_value();
                        args.push(value == null ? false : value);
                        return;
                    } else {
                        var splitted = field.split('.');
                        if (splitted.length > 1 && _.trim(splitted[0]) === "parent" && self.dataset.parent_view) {
                            if (parent_fields === null) {
                                parent_fields = self.dataset.parent_view.get_fields_values();
                            }
                            var p_val = parent_fields[_.trim(splitted[1])];
                            if (p_val !== undefined) {
                                args.push(p_val == null ? false : p_val);
                                return;
                            }
                        }
                    }
                    throw "Could not get field with name '" + field +
                        "' for onchange '" + onchange + "'";
                });
                var ajax = {
                    url: '/base/dataset/call',
                    async: false
                };
                return this.rpc(ajax, {
                    model: this.dataset.model,
                    method: method,
                    args: [(this.datarecord.id == null ? [] : [this.datarecord.id])].concat(args),
                    context_id: context_index === null ? null : context_index + 1
                }, function(response) {
                    self.on_processed_onchange(response, processed);
                });
            } else {
                this.log("Wrong on_change format", on_change);
            }
        }
    },
    on_processed_onchange: function(response, processed) {
        var result = response;
        if (result.value) {
            for (var f in result.value) {
                var field = this.fields[f];
                // If field is not defined in the view, just ignore it
                if (field) {
                    var value = result.value[f];
                    processed.push(field.name);
                    if (field.get_value() != value) {
                        field.set_value(value);
                        field.dirty = true;
                        if (_.indexOf(processed, field.name) < 0) {
                            this.do_onchange(field, processed);
                        }
                    }
                }
            }
            this.on_form_changed();
        }
        if (!_.isEmpty(result.warning)) {
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
            // TODO: 
        }
        this.ready = true;
    },
    on_button_new: function() {
        var self = this;
        var def = $.Deferred();
        $.when(this.has_been_loaded).then(function() {
            self.dataset.default_get(
                _.keys(self.fields_view.fields)).then(self.on_record_loaded).then(function() {
                    def.resolve();
                    });
        });
        return def.promise();
    },
    /**
     * Triggers saving the form's record. Chooses between creating a new
     * record or saving an existing one depending on whether the record
     * already has an id property.
     *
     * @param {Function} success callback on save success
     * @param {Boolean} [prepend_on_create=false] if ``do_save`` creates a new record, should that record be inserted at the start of the dataset (by default, records are added at the end)
     */
    do_save: function(success, prepend_on_create) {
        var self = this;
        if (!this.ready) {
            return false;
        }
        var form_dirty = false,
            form_invalid = false,
            values = {},
            first_invalid_field = null;
        for (var f in this.fields) {
            f = this.fields[f];
            if (!f.is_valid()) {
                form_invalid = true;
                f.update_dom();
                if (!first_invalid_field) {
                    first_invalid_field = f;
                }
            } else if (f.is_dirty()) {
                form_dirty = true;
                values[f.name] = f.get_value();
            }
        }
        if (form_invalid) {
            first_invalid_field.focus();
            this.on_invalid();
            return false;
        } else if (form_dirty) {
            this.log("About to save", values);
            if (!this.datarecord.id) {
                return this.dataset.create(values, function(r) {
                    self.on_created(r, success, prepend_on_create);
                });
            } else {
                return this.dataset.write(this.datarecord.id, values, function(r) {
                    self.on_saved(r, success);
                });
            }
        } else {
            return false;
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
            if (!f.is_valid()) {
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
            this.reload();
        }
    },
    /**
     * Updates the form' dataset to contain the new record:
     *
     * * Adds the newly created record to the current dataset (at the end by
     *   default)
     * * Selects that record (sets the dataset's index to point to the new
     *   record's id).
     * * Updates the pager and sidebar displays
     *
     * @param {Object} r
     * @param {Function} success callback to execute after having updated the dataset
     * @param {Boolean} [prepend_on_create=false] adds the newly created record at the beginning of the dataset instead of the end
     */
    on_created: function(r, success, prepend_on_create) {
        if (!r.result) {
            this.notification.warn("Record not created", "Problem while creating record.");
        } else {
            this.datarecord.id = r.result;
            if (!prepend_on_create) {
                this.dataset.ids.push(this.datarecord.id);
                this.dataset.index = this.dataset.ids.length - 1;
            } else {
                this.dataset.ids.unshift(this.datarecord.id);
                this.dataset.index = 0;
            }
            this.do_update_pager();
            if (this.sidebar) {
                this.sidebar.attachments.do_update();
            }
            this.notification.notify("Record created", "The record has been created with id #" + this.datarecord.id);
            if (success) {
                success(_.extend(r, {created: true}));
            }
            this.reload();
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
    },
    get_fields_values: function() {
        var values = {};
        _.each(this.fields, function(value, key) {
            var val = value.get_value();
            values[key] = val;
        });
        return values;
    }
});

/** @namespace */
openerp.base.form = {};

openerp.base.form.SidebarAttachments = openerp.base.Widget.extend({
    init: function(parent, element_id, form_view) {
        this._super(parent, element_id);
        this.view = form_view;
    },
    do_update: function() {
        if (!this.view.datarecord.id) {
            this.on_attachments_loaded([]);
        } else {
            (new openerp.base.DataSetSearch(
                this, 'ir.attachment', this.view.dataset.get_context(),
                [
                    ['res_model', '=', this.view.dataset.model],
                    ['res_id', '=', this.view.datarecord.id],
                    ['type', 'in', ['binary', 'url']]
                ])).read_slice(['name', 'url', 'type'], this.on_attachments_loaded);
        }
    },
    on_attachments_loaded: function(attachments) {
        this.attachments = attachments;
        this.$element.html(QWeb.render('FormView.sidebar.attachments', this));
        this.$element.find('.oe-binary-file').change(this.on_attachment_changed);
        this.$element.find('.oe-sidebar-attachment-delete').click(this.on_attachment_delete);
    },
    on_attachment_changed: function(e) {
        window[this.element_id + '_iframe'] = this.do_update;
        var $e = $(e.target);
        if ($e.val() != '') {
            this.$element.find('form.oe-binary-form').submit();
            $e.parent().find('input[type=file]').attr('disabled', 'true');
            $e.parent().find('button').attr('disabled', 'true').find('img, span').toggle();
        }
    },
    on_attachment_delete: function(e) {
        var self = this, $e = $(e.currentTarget);
        var name = _.trim($e.parent().find('a.oe-sidebar-attachments-link').text());
        if (confirm("Do you really want to delete the attachment " + name + " ?")) {
            this.rpc('/base/dataset/unlink', {
                model: 'ir.attachment',
                ids: [parseInt($e.attr('data-id'))]
            }, function(r) {
                $e.parent().remove();
                self.notification.notify("Delete an attachment", "The attachment '" + name + "' has been deleted");
            });
        }
    }
});

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

        var field = fields[ex[0]];
        if (!field) {
            throw new Error("Domain references unknown field : " + ex[0]);
        }
        var field_value = field.get_value ? fields[ex[0]].get_value() : fields[ex[0]].value;
        var op = ex[1];
        var val = ex[2];

        switch (op.toLowerCase()) {
            case '=':
            case '==':
                stack.push(field_value == val);
                break;
            case '!=':
            case '<>':
                stack.push(field_value != val);
                break;
            case '<':
                stack.push(field_value < val);
                break;
            case '>':
                stack.push(field_value > val);
                break;
            case '<=':
                stack.push(field_value <= val);
                break;
            case '>=':
                stack.push(field_value >= val);
                break;
            case 'in':
                stack.push(_(val).contains(field_value));
                break;
            case 'not in':
                stack.push(!_(val).contains(field_value));
                break;
            default:
                this.log("Unsupported operator in modifiers :", op);
        }
    }
    return _.all(stack, _.identity);
};

openerp.base.form.Widget = openerp.base.Widget.extend({
    template: 'Widget',
    init: function(view, node) {
        this.view = view;
        this.node = node;
        this.modifiers = JSON.parse(this.node.attrs.modifiers || '{}');
        this.type = this.type || node.tag;
        this.element_name = this.element_name || this.type;
        this.element_id = [this.view.element_id, this.element_name, this.view.widgets_counter++].join("_");

        this._super(view, this.element_id);

        this.view.widgets[this.element_id] = this;
        this.children = node.children;
        this.colspan = parseInt(node.attrs.colspan || 1);

        this.string = this.string || node.attrs.string;
        this.help = this.help || node.attrs.help;
        this.invisible = this.modifiers['invisible'] === true;
    },
    start: function() {
        this.$element = $('#' + this.element_id);
    },
    stop: function() {
        this.$element.remove();
    },
    process_modifiers: function() {
        var compute_domain = openerp.base.form.compute_domain;
        for (var a in this.modifiers) {
            this[a] = compute_domain(this.modifiers[a], this.view.fields);
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
    template: 'WidgetFrame',
    init: function(view, node) {
        this._super(view, node);
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
        var type = {};
        if (node.tag == 'field') {
            type = this.view.fields_view.fields[node.attrs.name] || {};
        }
        var widget = new (this.view.registry.get_any(
                [node.attrs.widget, type.type, node.tag])) (this.view, node);
        if (node.tag == 'field') {
            if (!this.view.default_focus_field || node.attrs.default_focus == '1') {
                this.view.default_focus_field = widget;
            }
            if (node.attrs.nolabel != '1') {
                var label = new (this.view.registry.get_object('label')) (this.view, node);
                label["for"] = widget;
                this.add_widget(label, widget.colspan + 1);
            }
        }
        this.add_widget(widget);
    },
    add_widget: function(widget, colspan) {
        colspan = colspan || widget.colspan;
        var current_row = this.table[this.table.length - 1];
        if (current_row.length && (this.x + colspan) > this.columns) {
            current_row = this.add_row();
        }
        current_row.push(widget);
        this.x += widget.colspan;
        return widget;
    }
});

openerp.base.form.WidgetNotebook = openerp.base.form.Widget.extend({
    template: 'WidgetNotebook',
    init: function(view, node) {
        this._super(view, node);
        this.pages = [];
        for (var i = 0; i < node.children.length; i++) {
            var n = node.children[i];
            if (n.tag == "page") {
                var page = new openerp.base.form.WidgetNotebookPage(this.view, n, this, this.pages.length);
                this.pages.push(page);
            }
        }
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element.tabs();
        this.view.on_button_new.add_last(this.do_select_first_visible_tab);
    },
    do_select_first_visible_tab: function() {
        for (var i = 0; i < this.pages.length; i++) {
            var page = this.pages[i];
            if (page.invisible === false) {
                this.$element.tabs('select', page.index);
                break;
            }
        }
    }
});

openerp.base.form.WidgetNotebookPage = openerp.base.form.WidgetFrame.extend({
    template: 'WidgetNotebookPage',
    init: function(view, node, notebook, index) {
        this.notebook = notebook;
        this.index = index;
        this.element_name = 'page_' + index;
        this._super(view, node);
        this.element_tab_id = this.element_id + '_tab';
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element_tab = $('#' + this.element_tab_id);
    },
    update_dom: function() {
        if (this.invisible && this.index === this.notebook.$element.tabs('option', 'selected')) {
            this.notebook.do_select_first_visible_tab();
        }
        this.$element_tab.toggle(!this.invisible);
        this.$element.toggle(!this.invisible);
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
        if (this.string) {
            // We don't have button key bindings in the webclient
            this.string = this.string.replace(/_/g, '');
        }
        if (node.attrs.default_focus == '1') {
            // TODO fme: provide enter key binding to widgets
            this.view.default_focus_button = this;
        }
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element.click(this.on_click);
    },
    on_click: function(saved) {
        var self = this;
        if (!this.node.attrs.special && this.view.dirty && saved !== true) {
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
            this.node.attrs, this.view.dataset, this.view.datarecord.id, function () {
                self.view.reload();
            });
    }
});

openerp.base.form.WidgetLabel = openerp.base.form.Widget.extend({
    init: function(view, node) {
        this.element_name = 'label_' + node.attrs.name;

        this._super(view, node);

        // TODO fme: support for attrs.align
        if (this.node.tag == 'label' && this.node.attrs.colspan) {
            this.is_field_label = false;
            this.template = "WidgetParagraph";
            this.colspan = this.node.attrs.colspan;
        } else {
            this.is_field_label = true;
            this.template = "WidgetLabel";
            this.colspan = 1;
        }
    },
    render: function () {
        if (this['for'] && this.type !== 'label') {
            return QWeb.render(this.template, {widget: this['for']});
        }
        // Actual label widgets should not have a false and have type label
        return QWeb.render(this.template, {widget: this});
    },
    start: function() {
        this._super();
        var self = this;
        this.$element.find("label").dblclick(function() {
            var widget = self['for'] || self;
            self.log(widget.element_id , widget);
            window.w = widget;
        });
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
        this.nolabel = (this.field.nolabel || node.attrs.nolabel) === '1';
        this.readonly = this.modifiers['readonly'] === true;
        this.required = this.modifiers['required'] === true;
        this.invalid = false;
        this.dirty = false;
    },
    set_value: function(value) {
        this.value = value;
        this.invalid = false;
        this.update_dom();
        this.on_value_changed();
    },
    set_value_from_ui: function() {
        this.on_value_changed();
    },
    on_value_changed: function() {
    },
    get_value: function() {
        return this.value;
    },
    is_valid: function() {
        return !this.invalid;
    },
    is_dirty: function() {
        return this.dirty;
    },
    get_on_change_value: function() {
        return this.get_value();
    },
    update_dom: function() {
        this._super.apply(this, arguments);
        if (!this.disable_utility_classes) {
            this.$element.toggleClass('disabled', this.readonly);
            this.$element.toggleClass('required', this.required);
            if (this.view.show_invalid) {
                this.$element.toggleClass('invalid', !this.is_valid());
            }
        }
    },
    on_ui_change: function() {
        this.dirty = this.view.dirty = true;
        this.validate();
        if (this.is_valid()) {
            this.set_value_from_ui();
            this.view.do_onchange(this);
            this.view.on_form_changed();
        } else {
            this.update_dom();
        }
    },
    validate: function() {
        this.invalid = false;
    },
    focus: function() {
    },
    _build_view_fields_values: function() {
        var a_dataset = this.view.dataset || {};
        var fields_values = this.view.get_fields_values();
        var parent_values = a_dataset.parent_view ? a_dataset.parent_view.get_fields_values() : {};
        fields_values.parent = parent_values;
        return fields_values;
    },
    /**
     * Builds a new context usable for operations related to fields by merging
     * the fields'context with the action's context.
     */
    build_context: function() {
        // I previously belevied contexts should be herrited, but now I doubt it
        //var a_context = this.view.dataset.get_context() || {};
        var f_context = this.field.context || null;
        // maybe the default_get should only be used when we do a default_get?
        var v_context1 = this.node.attrs.default_get || {};
        var v_context2 = this.node.attrs.context || {};
        var v_context = new openerp.base.CompoundContext(v_context1, v_context2);
        if (v_context1.__ref || v_context2.__ref || true) { //TODO niv: remove || true
            var fields_values = this._build_view_fields_values();
            v_context.set_eval_context(fields_values);
        }
        // if there is a context on the node, overrides the model's context
        var ctx = f_context || v_context;
        return ctx;
    },
    build_domain: function() {
        var f_domain = this.field.domain || null;
        var v_domain = this.node.attrs.domain || [];
        if (!(v_domain instanceof Array) || true) { //TODO niv: remove || true
            var fields_values = this._build_view_fields_values();
            v_domain = new openerp.base.CompoundDomain(v_domain).set_eval_context(fields_values);
        }
        // if there is a domain on the node, overrides the model's domain
        return f_domain || v_domain;
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
        this._super();
    },
    validate: function() {
        this.invalid = false;
        var value = this.$element.find('input').val();
        if (value === "") {
            this.invalid = this.required;
        } else if (this.validation_regex) {
            this.invalid = !this.validation_regex.test(value);
        }
    },
    focus: function() {
        this.$element.find('input').focus();
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
        if (!this.value || !this.is_valid()) {
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
        this._super.apply(this, [value]);
        if (value === false || value === undefined) {
            // As in GTK client, floats default to 0
            value = 0;
            this.dirty = true;
        }
        var show_value = value.toFixed(2);
        this.$element.find('input').val(show_value);
    },
    set_value_from_ui: function() {
        this.value = Number(this.$element.find('input').val().replace(/,/g, '.'));
        this._super();
    }
});

openerp.base.form.FieldInteger = openerp.base.form.FieldFloat.extend({
    init: function(view, node) {
        this._super(view, node);
        this.validation_regex = /^-?\d+$/;
    },
    set_value: function(value) {
        this._super.apply(this, [value]);
        if (value === false || value === undefined) {
            // TODO fme: check if GTK client default integers to 0 (like it does with floats)
            value = 0;
            this.dirty = true;
        }
        var show_value = parseInt(value, 10);
        this.$element.find('input').val(show_value);
    },
    set_value_from_ui: function() {
        this.value = Number(this.$element.find('input').val());
        this._super();
    }
});

openerp.base.form.FieldDatetime = openerp.base.form.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldDate";
        this.jqueryui_object = 'datetimepicker';
        this.validation_regex = /^\d+-\d+-\d+( \d+:\d+(:\d+)?)?$/;
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element.find('input').change(this.on_ui_change)[this.jqueryui_object]({
            dateFormat: 'yy-mm-dd',
            timeFormat: 'hh:mm:ss',
            showOn: 'button',
            buttonImage: '/base/static/src/img/ui/field_calendar.png',
            buttonImageOnly: true,
            constrainInput: false
        });
    },
    set_value: function(value) {
        this._super.apply(this, arguments);
        if (!value) {
            this.$element.find('input').val('');
        } else {
            this.$element.find('input').unbind('change');
            // jQuery UI date picker wrongly call on_change event herebelow
            this.$element.find('input')[this.jqueryui_object]('setDate', this.parse(value));
            this.$element.find('input').change(this.on_ui_change);
        }
    },
    set_value_from_ui: function() {
        this.value = this.$element.find('input')[this.jqueryui_object]('getDate') || false;
        if (this.value) {
            this.value = this.format(this.value);
        }
        this._super();
    },
    update_dom: function() {
        this._super.apply(this, arguments);
        this.$element.find('input').datepicker(this.readonly ? 'disable' : 'enable');
    },
    validate: function() {
        this.invalid = false;
        var value = this.$element.find('input').val();
        if (value === "") {
            this.invalid = this.required;
        } else if (this.validation_regex) {
            this.invalid = !this.validation_regex.test(value);
        } else {
            this.invalid = !this.$element.find('input')[this.jqueryui_object]('getDate');
        }
    },
    focus: function() {
        this.$element.find('input').focus();
    },
    parse: openerp.base.str_to_datetime,
    format: openerp.base.datetime_to_str
});

openerp.base.form.FieldDate = openerp.base.form.FieldDatetime.extend({
    init: function(view, node) {
        this._super(view, node);
        this.jqueryui_object = 'datepicker';
        this.validation_regex = /^\d+-\d+-\d+$/;
    },
    parse: openerp.base.str_to_date,
    format: openerp.base.date_to_str
});

openerp.base.form.FieldFloatTime = openerp.base.form.FieldChar.extend({
    init: function(view, node) {
        this._super(view, node);
        this.validation_regex = /^\d+:\d+$/;
    },
    set_value: function(value) {
        this._super.apply(this, [value]);
        if (value === false || value === undefined) {
            // As in GTK client, floats default to 0
            value = 0;
            this.dirty = true;
        }
        var show_value = _.sprintf("%02d:%02d", Math.floor(value), Math.round((value % 1) * 60));
        this.$element.find('input').val(show_value);
    },
    set_value_from_ui: function() {
        var time = this.$element.find('input').val().split(':');
        this.set_value(parseInt(time[0], 10) + parseInt(time[1], 10) / 60);
        this._super();
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
        this._super();
    },
    validate: function() {
        this.invalid = false;
        var value = this.$element.find('textarea').val();
        if (value === "") {
            this.invalid = this.required;
        } else if (this.validation_regex) {
            this.invalid = !this.validation_regex.test(value);
        }
    },
    focus: function() {
        this.$element.find('textarea').focus();
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
        this._super();
    },
    update_dom: function() {
        this._super.apply(this, arguments);
        this.$element.find('input').attr('disabled', this.readonly);
    },
    validate: function() {
        this.invalid = this.required && !this.$element.find('input').is(':checked');
    },
    focus: function() {
        this.$element.find('input').focus();
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
        if (isNaN(show_value)) {
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
        this.field_index = _.map(this.field.selection, function(x, index) {
            return {"ikey": "" + index, "ekey": x[0], "label": x[1]};
        });
    },
    start: function() {
        // Flag indicating whether we're in an event chain containing a change
        // event on the select, in order to know what to do on keyup[RETURN]:
        // * If the user presses [RETURN] as part of changing the value of a
        //   selection, we should just let the value change and not let the
        //   event broadcast further (e.g. to validating the current state of
        //   the form in editable list view, which would lead to saving the
        //   current row or switching to the next one)
        // * If the user presses [RETURN] with a select closed (side-effect:
        //   also if the user opened the select and pressed [RETURN] without
        //   changing the selected value), takes the action as validating the
        //   row
        var ischanging = false;
        this._super.apply(this, arguments);
        this.$element.find('select')
            .change(this.on_ui_change)
            .change(function () { ischanging = true; })
            .click(function () { ischanging = false; })
            .keyup(function (e) {
                if (e.which !== 13 || !ischanging) { return; }
                e.stopPropagation();
                ischanging = false;
            });
    },
    set_value: function(value) {
        value = value === null ? false : value;
        value = value instanceof Array ? value[0] : value;
        this._super(value);
        var option = _.detect(this.field_index, function(x) {return x.ekey === value;});
        this.$element.find('select').val(option === undefined ? '' : option.ikey);
    },
    set_value_from_ui: function() {
        var ikey = this.$element.find('select').val();
        var option = _.detect(this.field_index, function(x) {return x.ikey === ikey;});
        this.value = option === undefined ? false : option.ekey;
        this._super();
    },
    update_dom: function() {
        this._super.apply(this, arguments);
        this.$element.find('select').attr('disabled', this.readonly);
    },
    validate: function() {
        var ikey = this.$element.find('select').val();
        var option = _.detect(this.field_index, function(x) {return x.ikey === ikey;});
        this.invalid = this.required && (option === undefined || option.ekey === false);
    },
    focus: function() {
        this.$element.find('select').focus();
    }
});

// jquery autocomplete tweak to allow html
(function() {
    var proto = $.ui.autocomplete.prototype,
        initSource = proto._initSource;

    function filter( array, term ) {
        var matcher = new RegExp( $.ui.autocomplete.escapeRegex(term), "i" );
        return $.grep( array, function(value) {
            return matcher.test( $( "<div>" ).html( value.label || value.value || value ).text() );
        });
    }

    $.extend( proto, {
        _initSource: function() {
            if ( this.options.html && $.isArray(this.options.source) ) {
                this.source = function( request, response ) {
                    response( filter( this.options.source, request.term ) );
                };
            } else {
                initSource.call( this );
            }
        },

        _renderItem: function( ul, item) {
            return $( "<li></li>" )
                .data( "item.autocomplete", item )
                .append( $( "<a></a>" )[ this.options.html ? "html" : "text" ]( item.label ) )
                .appendTo( ul );
        }
    });
})();

openerp.base.form.dialog = function(content, options) {
    options = _.extend({
        autoOpen: true,
        width: '90%',
        height: '90%',
        min_width: '800px',
        min_height: '600px'
    }, options || {});
    options.autoOpen = true;
    var dialog = new openerp.base.Dialog(null, options);
    dialog.$dialog = $(content).dialog(dialog.dialog_options);
    return dialog.$dialog;
}

openerp.base.form.FieldMany2One = openerp.base.form.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldMany2One";
        this.limit = 7;
        this.value = null;
        this.cm_id = _.uniqueId('m2o_cm_');
        this.last_search = [];
        this.tmp_value = undefined;
    },
    start: function() {
        this._super();
        var self = this;
        this.$input = this.$element.find("input");
        this.$drop_down = this.$element.find(".oe-m2o-drop-down-button");
        this.$menu_btn = this.$element.find(".oe-m2o-cm-button");

        // context menu
        var bindings = {};
        bindings[this.cm_id + "_search"] = function() {
            self._search_create_popup("search");
        };
        bindings[this.cm_id + "_create"] = function() {
            self._search_create_popup("form");
        };
        bindings[this.cm_id + "_open"] = function() {
            if (!self.value) {
                return;
            }
            var pop = new openerp.base.form.FormOpenPopup(self.view);
            pop.show_element(self.field.relation, self.value[0],self.build_context(), {});
            pop.on_write_completed.add_last(function() {
                self.set_value(self.value[0]);
            });
        };
        var cmenu = this.$menu_btn.contextMenu(this.cm_id, {'leftClickToo': true,
            bindings: bindings, itemStyle: {"color": ""},
            onContextMenu: function() {
                if(self.value) {
                    $("#" + self.cm_id + "_open").removeClass("oe-m2o-disabled-cm");
                } else {
                    $("#" + self.cm_id + "_open").addClass("oe-m2o-disabled-cm");
                }
                return true;
            }
        });

        // some behavior for input
        this.$input.keyup(function() {
            if (self.$input.val() === "") {
                self._change_int_value(null);
            } else if (self.value === null || (self.value && self.$input.val() !== self.value[1])) {
                self._change_int_value(undefined);
            }
        });
        this.$drop_down.click(function() {
            if (self.$input.autocomplete("widget").is(":visible")) {
                self.$input.autocomplete("close");
            } else {
                if (self.value) {
                    self.$input.autocomplete("search", "");
                } else {
                    self.$input.autocomplete("search");
                }
                self.$input.focus();
            }
        });
        var anyoneLoosesFocus = function() {
            if (!self.$input.is(":focus") &&
                    !self.$input.autocomplete("widget").is(":visible") &&
                    !self.value) {
                if(self.value === undefined && self.last_search.length > 0) {
                    self._change_int_ext_value(self.last_search[0]);
                } else {
                    self._change_int_ext_value(null);
                }
            }
        }
        this.$input.focusout(anyoneLoosesFocus);

        var isSelecting = false;
        // autocomplete
        this.$input.autocomplete({
            source: function(req, resp) { self.get_search_result(req, resp); },
            select: function(event, ui) {
                isSelecting = true;
                var item = ui.item;
                if (item.id) {
                    self._change_int_value([item.id, item.name]);
                } else if (item.action) {
                    self._change_int_value(undefined);
                    item.action();
                    return false;
                }
            },
            focus: function(e, ui) {
                e.preventDefault();
            },
            html: true,
            close: anyoneLoosesFocus,
            minLength: 0,
            delay: 0
        });
        // used to correct a bug when selecting an element by pushing 'enter' in an editable list
        this.$input.keyup(function(e) {
            if (e.which === 13) {
                if (isSelecting)
                    e.stopPropagation();
            }
            isSelecting = false;
        });
    },
    // autocomplete component content handling
    get_search_result: function(request, response) {
        var search_val = request.term;
        var self = this;

        var dataset = new openerp.base.DataSetStatic(this, this.field.relation, self.build_context());

        dataset.name_search(search_val, self.build_domain(), 'ilike',
                this.limit + 1, function(data) {
            self.last_search = data;
            // possible selections for the m2o
            var values = _.map(data, function(x) {
                return {label: $('<span />').text(x[1]).html(), name:x[1], id:x[0]};
            });

            // search more... if more results that max
            if (values.length > self.limit) {
                values = values.slice(0, self.limit);
                values.push({label: _t("<em>   Search More...</em>"), action: function() {
                    dataset.name_search(search_val, self.build_domain(), 'ilike'
                    , false, function(data) {
                        self._change_int_value(null);
                        self._search_create_popup("search", data);
                    });
                }});
            }
            // quick create
            var raw_result = _(data.result).map(function(x) {return x[1];})
            if (search_val.length > 0 &&
                !_.include(raw_result, search_val) &&
                (!self.value || search_val !== self.value[1])) {
                values.push({label: _.sprintf(_t('<em>   Create "<strong>%s</strong>"</em>'),
                        $('<span />').text(search_val).html()), action: function() {
                    self._quick_create(search_val);
                }});
            }
            // create...
            values.push({label: _t("<em>   Create and Edit...</em>"), action: function() {
                self._change_int_value(null);
                self._search_create_popup("form", undefined, {"default_name": search_val});
            }});

            response(values);
        });
    },
    _quick_create: function(name) {
        var self = this;
        var dataset = new openerp.base.DataSetStatic(this, this.field.relation, self.build_context());
        dataset.name_create(name, function(data) {
            self._change_int_ext_value(data);
        }).fail(function(error, event) {
            event.preventDefault();
            self._change_int_value(null);
            self._search_create_popup("form", undefined, {"default_name": name});
        });
    },
    // all search/create popup handling
    _search_create_popup: function(view, ids, context) {
        var self = this;
        var pop = new openerp.base.form.SelectCreatePopup(this);
        pop.select_element(self.field.relation,{
                initial_ids: ids ? _.map(ids, function(x) {return x[0]}) : undefined,
                initial_view: view,
                disable_multiple_selection: true
                }, self.build_domain(),
                new openerp.base.CompoundContext(self.build_context(), context || {}));
        pop.on_select_elements.add(function(element_ids) {
            var dataset = new openerp.base.DataSetStatic(self, self.field.relation, self.build_context());
            dataset.name_get([element_ids[0]], function(data) {
                self._change_int_ext_value(data[0]);
            });
        });
    },
    _change_int_ext_value: function(value) {
        this._change_int_value(value);
        this.$input.val(this.value ? this.value[1] : "");
    },
    _change_int_value: function(value) {
        this.value = value;
        var back_orig_value = this.original_value;
        if (this.value === null || this.value) {
            this.original_value = this.value;
        }
        if (back_orig_value === undefined) { // first use after a set_value()
            return;
        }
        if (this.value !== undefined && ((back_orig_value ? back_orig_value[0] : null)
                !== (this.value ? this.value[0] : null))) {
            this.on_ui_change();
        }
    },
    set_value: function(value) {
        value = value || null;
        var self = this;
        var _super = this._super;
        this.tmp_value = value;
        var real_set_value = function(rval) {
            self.tmp_value = undefined;
            _super.apply(self, rval);
            self.original_value = undefined;
            self._change_int_ext_value(rval);
        };
        if(typeof(value) === "number") {
            var dataset = new openerp.base.DataSetStatic(this, this.field.relation, self.build_context());
            dataset.name_get([value], function(data) {
                real_set_value(data[0]);
            }).fail(function() {self.tmp_value = undefined;});
        } else {
            setTimeout(function() {real_set_value(value);}, 0);
        }
    },
    get_value: function() {
        if (this.tmp_value !== undefined) {
            if (this.tmp_value instanceof Array) {
                return this.tmp_value[0];
            }
            return this.tmp_value ? this.tmp_value : false;
        }
        if (this.value === undefined)
            return this.original_value ? this.original_value[0] : false;
        return this.value ? this.value[0] : false;
    },
    validate: function() {
        this.invalid = false;
        if (this.value === null) {
            this.invalid = this.required;
        }
    }
});

/*
# Values: (0, 0,  { fields })    create
#         (1, ID, { fields })    update
#         (2, ID)                remove (delete)
#         (3, ID)                unlink one (target id or target of relation)
#         (4, ID)                link
#         (5)                    unlink all (only valid for one2many)
*/
var commands = {
    // (0, _, {values})
    CREATE: 0,
    'create': function (values) {
        return [commands.CREATE, false, values];
    },
    // (1, id, {values})
    UPDATE: 1,
    'update': function (id, values) {
        return [commands.UPDATE, id, values];
    },
    // (2, id[, _])
    DELETE: 2,
    'delete': function (id) {
        return [commands.DELETE, id, false];
    },
    // (3, id[, _]) removes relation, but not linked record itself
    FORGET: 3,
    'forget': function (id) {
        return [commands.FORGET, id, false];
    },
    // (4, id[, _])
    LINK_TO: 4,
    'link_to': function (id) {
        return [commands.LINK_TO, id, false];
    },
    // (5[, _[, _]])
    DELETE_ALL: 5,
    'delete_all': function () {
        return [5, false, false];
    },
    // (6, _, ids) replaces all linked records with provided ids
    REPLACE_WITH: 6,
    'replace_with': function (ids) {
        return [6, false, ids];
    }
};
openerp.base.form.FieldOne2Many = openerp.base.form.Field.extend({
    multi_selection: false,
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldOne2Many";
        this.is_started = $.Deferred();
        this.form_last_update = $.Deferred();
        this.disable_utility_classes = true;
    },
    start: function() {
        this._super.apply(this, arguments);

        var self = this;

        this.dataset = new openerp.base.form.One2ManyDataSet(this, this.field.relation);
        this.dataset.o2m = this;
        this.dataset.parent_view = this.view;
        this.dataset.on_change.add_last(function() {
            self.on_ui_change();
        });

        var modes = this.node.attrs.mode;
        modes = !!modes ? modes.split(",") : ["tree", "form"];
        var views = [];
        _.each(modes, function(mode) {
            var view = {
                view_id: false,
                view_type: mode == "tree" ? "list" : mode,
                options: { sidebar : false }
            };
            if (self.field.views && self.field.views[mode]) {
                view.embedded_view = self.field.views[mode];
            }
            if(view.view_type === "list") {
                view.options.selectable = self.multi_selection;
            }
            views.push(view);
        });
        this.views = views;

        this.viewmanager = new openerp.base.ViewManager(this, this.dataset, views);
        this.viewmanager.registry = openerp.base.views.clone({
            list: 'openerp.base.form.One2ManyListView',
            form: 'openerp.base.form.One2ManyFormView'
        });
        var once = $.Deferred().then(function() {
            self.form_last_update.resolve();
        });
        this.viewmanager.on_controller_inited.add_last(function(view_type, controller) {
            if (view_type == "list") {
                controller.o2m = self;
            } else if (view_type == "form") {
                controller.on_record_loaded.add_last(function() {
                    once.resolve();
                });
                controller.on_pager_action.add_first(function() {
                    self.save_form_view();
                });
                controller.$element.find(".oe_form_button_save_edit").hide();
            }
            self.is_started.resolve();
        });
        this.viewmanager.on_mode_switch.add_first(function() {
            self.save_form_view();
        });
        setTimeout(function () {
            self.viewmanager.appendTo(self.$element);
        }, 0);
    },
    reload_current_view: function() {
        var self = this;
        var view = self.viewmanager.views[self.viewmanager.active_view].controller;
        if(self.viewmanager.active_view === "list") {
            view.reload_content();
        } else if (self.viewmanager.active_view === "form") {
            if (this.dataset.index === null && this.dataset.ids.length >= 1) {
                this.dataset.index = 0;
            }
            this.form_last_update.then(function() {
                this.form_last_update = view.do_show();
            });
        }
    },
    set_value: function(value) {
        value = value || [];
        var self = this;
        this.dataset.reset_ids([]);
        if(value.length >= 1 && value[0] instanceof Array) {
            var ids = [];
            _.each(value, function(command) {
                var obj = {values: command[2]};
                switch (command[0]) {
                    case commands.CREATE:
                        obj['id'] = _.uniqueId(self.dataset.virtual_id_prefix);
                        self.dataset.to_create.push(obj);
                        self.dataset.cache.push(_.clone(obj));
                        ids.push(obj.id);
                        return;
                    case commands.UPDATE:
                        obj['id'] = command[1];
                        self.dataset.to_write.push(obj);
                        self.dataset.cache.push(_.clone(obj));
                        ids.push(obj.id);
                        return;
                    case commands.DELETE:
                        self.dataset.to_delete.push({id: command[1]});
                        return;
                    case commands.LINK_TO:
                        ids.push(command[1]);
                        return;
                    case commands.DELETE_ALL:
                        self.dataset.delete_all = true;
                        return;
                }
            });
            this._super(ids);
            this.dataset.set_ids(ids);
        } else if (value.length >= 1 && typeof(value[0]) === "object") {
            var ids = [];
            this.dataset.delete_all = true;
            _.each(value, function(command) {
                var obj = {values: command};
                obj['id'] = _.uniqueId(self.dataset.virtual_id_prefix);
                self.dataset.to_create.push(obj);
                self.dataset.cache.push(_.clone(obj));
                ids.push(obj.id);
            });
            this._super(ids);
            this.dataset.set_ids(ids);
        } else {
            this._super(value);
            this.dataset.reset_ids(value);
        }
        if (this.dataset.index === null && this.dataset.ids.length > 0) {
            this.dataset.index = 0;
        }
        $.when(this.is_started).then(function() {
            self.reload_current_view();
        });
    },
    get_value: function() {
        var self = this;
        if (!this.dataset)
            return [];
        var val = this.dataset.delete_all ? [commands.delete_all()] : [];
        val = val.concat(_.map(this.dataset.ids, function(id) {
            var alter_order = _.detect(self.dataset.to_create, function(x) {return x.id === id;});
            if (alter_order) {
                return commands.create(alter_order.values);
            }
            alter_order = _.detect(self.dataset.to_write, function(x) {return x.id === id;});
            if (alter_order) {
                return commands.update(alter_order.id, alter_order.values);
            }
            return commands.link_to(id);
        }));
        return val.concat(_.map(
            this.dataset.to_delete, function(x) {
                return commands['delete'](x.id);}));
    },
    save_form_view: function() {
        if (this.viewmanager && this.viewmanager.views && this.viewmanager.active_view &&
            this.viewmanager.views[this.viewmanager.active_view] &&
            this.viewmanager.views[this.viewmanager.active_view].controller) {
            var view = this.viewmanager.views[this.viewmanager.active_view].controller;
            if (this.viewmanager.active_view === "form") {
                var res = view.do_save();
                if (res === false) {
                    // ignore
                } else if (res.isRejected()) {
                    throw "Save or create on one2many dataset is not supposed to fail.";
                } else if (!res.isResolved()) {
                    throw "Asynchronous get_value() is not supported in form view.";
                }
                return res;
            }
        }
        return false;
    },
    is_valid: function() {
        this.validate();
        return this._super();
    },
    validate: function() {
        this.invalid = false;
        var self = this;
        var view = self.viewmanager.views[self.viewmanager.active_view].controller;
        if (self.viewmanager.active_view === "form") {
            for (var f in view.fields) {
                f = view.fields[f];
                if (!f.is_valid()) {
                    this.invalid = true;
                    return;
                }
            }
        }
    },
    is_dirty: function() {
        this.save_form_view();
        return this._super();
    },
    update_dom: function() {
        this._super.apply(this, arguments);
        this.$element.toggleClass('disabled', this.readonly);
    }
});

openerp.base.form.One2ManyDataSet = openerp.base.BufferedDataSet.extend({
    get_context: function() {
        this.context = this.o2m.build_context();
        return this.context;
    }
});

openerp.base.form.One2ManyFormView = openerp.base.FormView.extend({
    
});

openerp.base.form.One2ManyListView = openerp.base.ListView.extend({
    do_add_record: function () {
        if (this.options.editable) {
            this._super.apply(this, arguments);
        } else {
            var self = this;
            var pop = new openerp.base.form.SelectCreatePopup(this);
            pop.select_element(self.o2m.field.relation,{
                initial_view: "form",
                alternative_form_view: self.o2m.field.views ? self.o2m.field.views["form"] : undefined,
                create_function: function(data) {
                    return self.o2m.dataset.create(data, function(r) {
                        self.o2m.dataset.set_ids(self.o2m.dataset.ids.concat([r.result]));
                        self.o2m.dataset.on_change();
                    });
                },
                parent_view: self.o2m.view
            }, self.o2m.build_domain(), self.o2m.build_context());
            pop.on_select_elements.add_last(function() {
                self.o2m.reload_current_view();
            });
        }
    },
    do_activate_record: function(index, id) {
        var self = this;
        var pop = new openerp.base.form.FormOpenPopup(self.o2m.view);
        pop.show_element(self.o2m.field.relation, id, self.o2m.build_context(),{
            auto_write: false,
            alternative_form_view: self.o2m.field.views ? self.o2m.field.views["form"] : undefined,
            parent_view: self.o2m.view
        });
        pop.on_write.add(function(id, data) {
            self.o2m.dataset.write(id, data, function(r) {
                self.o2m.reload_current_view();
            });
        });
    }
});

openerp.base.form.FieldMany2Many = openerp.base.form.Field.extend({
    multi_selection: false,
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldMany2Many";
        this.list_id = _.uniqueId("many2many");
        this.is_started = $.Deferred();
    },
    start: function() {
        this._super.apply(this, arguments);

        var self = this;

        this.dataset = new openerp.base.form.Many2ManyDataSet(this, this.field.relation);
        this.dataset.m2m = this;
        this.dataset.on_unlink.add_last(function(ids) {
            self.on_ui_change();
        });

        this.list_view = new openerp.base.form.Many2ManyListView(this, this.list_id, this.dataset, false, {
                    'addable': 'Add',
                    'selectable': self.multi_selection
            });
        this.list_view.m2m_field = this;
        this.list_view.on_loaded.add_last(function() {
            self.is_started.resolve();
        });
        setTimeout(function () {
            self.list_view.start();
        }, 0);
    },
    set_value: function(value) {
        value = value || [];
        if (value.length >= 1 && value[0] instanceof Array) {
            value = value[0][2];
        }
        this._super(value);
        this.dataset.set_ids(value);
        var self = this;
        $.when(this.is_started).then(function() {
            self.list_view.reload_content();
        });
    },
    get_value: function() {
        return [commands.replace_with(this.dataset.ids)];
    },
    validate: function() {
        this.invalid = false;
        // TODO niv
    }
});

openerp.base.form.Many2ManyDataSet = openerp.base.DataSetStatic.extend({
    get_context: function() {
        this.context = this.m2m.build_context();
        return this.context;
    }
});

openerp.base.form.Many2ManyListView = openerp.base.ListView.extend({
    do_add_record: function () {
        var pop = new openerp.base.form.SelectCreatePopup(this);
        pop.select_element(this.model, {},
            new openerp.base.CompoundDomain(this.m2m_field.build_domain(), ["!", ["id", "in", this.m2m_field.dataset.ids]]),
            this.m2m_field.build_context());
        var self = this;
        pop.on_select_elements.add(function(element_ids) {
            _.each(element_ids, function(element_id) {
                if(! _.detect(self.dataset.ids, function(x) {return x == element_id;})) {
                    self.dataset.set_ids([].concat(self.dataset.ids, [element_id]));
                    self.m2m_field.on_ui_change();
                    self.reload_content();
                }
            });
        });
    },
    do_activate_record: function(index, id) {
        var self = this;
        var pop = new openerp.base.form.FormOpenPopup(this);
        pop.show_element(this.dataset.model, id, this.m2m_field.build_context(), {});
        pop.on_write_completed.add_last(function() {
            self.reload_content();
        });
    }
});

openerp.base.form.SelectCreatePopup = openerp.base.OldWidget.extend({
    identifier_prefix: "selectcreatepopup",
    template: "SelectCreatePopup",
    /**
     * options:
     * - initial_ids
     * - initial_view: form or search (default search)
     * - disable_multiple_selection
     * - alternative_form_view
     * - create_function (defaults to a naive saving behavior)
     * - parent_view
     */
    select_element: function(model, options, domain, context) {
        var self = this;
        this.model = model;
        this.domain = domain || [];
        this.context = context || {};
        this.options = _.defaults(options || {}, {"initial_view": "search", "create_function": function() {
            return self.create_row.apply(self, arguments);
        }});
        this.initial_ids = this.options.initial_ids;
        this.created_elements = [];
        openerp.base.form.dialog(this.render(), {close:function() {
            self.check_exit();
        }});
        this.start();
    },
    start: function() {
        this._super();
        this.dataset = new openerp.base.ReadOnlyDataSetSearch(this, this.model,
            this.context);
        this.dataset.parent_view = this.options.parent_view;
        if (this.options.initial_view == "search") {
            this.setup_search_view();
        } else { // "form"
            this.new_object();
        }
    },
    setup_search_view: function() {
        var self = this;
        if (this.searchview) {
            this.searchview.stop();
        }
        this.searchview = new openerp.base.SearchView(this,
                this.element_id + "_search", this.dataset, false, {
                    "selectable": !this.options.disable_multiple_selection,
                    "deletable": false
                });
        this.searchview.on_search.add(function(domains, contexts, groupbys) {
            if (self.initial_ids) {
                self.view_list.do_search.call(self, domains.concat([[["id", "in", self.initial_ids]], self.domain]),
                    contexts, groupbys);
                self.initial_ids = undefined;
            } else {
                self.view_list.do_search.call(self, domains.concat([self.domain]), contexts, groupbys);
            }
        });
        this.searchview.on_loaded.add_last(function () {
            var $buttons = self.searchview.$element.find(".oe_search-view-buttons");
            $buttons.append(QWeb.render("SelectCreatePopup.search.buttons"));
            var $cbutton = $buttons.find(".oe_selectcreatepopup-search-close");
            $cbutton.click(function() {
                self.stop();
            });
            var $sbutton = $buttons.find(".oe_selectcreatepopup-search-select");
            if(self.options.disable_multiple_selection) {
                $sbutton.hide();
            }
            $sbutton.click(function() {
                self.on_select_elements(self.selected_ids);
                self.stop();
            });
            self.view_list = new openerp.base.form.SelectCreateListView(self,
                    self.element_id + "_view_list", self.dataset, false,
                    {'deletable': false});
            self.view_list.popup = self;
            self.view_list.do_show();
            self.view_list.start().then(function() {
                self.searchview.do_search();
            });
        });
        this.searchview.start();
    },
    create_row: function(data) {
        var self = this;
        var wdataset = new openerp.base.DataSetSearch(this, this.model, this.context, this.domain);
        wdataset.parent_view = this.options.parent_view;
        return wdataset.create(data);
    },
    on_select_elements: function(element_ids) {
    },
    on_click_element: function(ids) {
        this.selected_ids = ids || [];
        if(this.selected_ids.length > 0) {
            this.$element.find(".oe_selectcreatepopup-search-select").removeAttr('disabled');
        } else {
            this.$element.find(".oe_selectcreatepopup-search-select").attr('disabled', "disabled");
        }
    },
    new_object: function() {
        var self = this;
        if (this.searchview) {
            this.searchview.hide();
        }
        if (this.view_list) {
            this.view_list.$element.hide();
        }
        this.dataset.index = null;
        this.view_form = new openerp.base.FormView(this, this.element_id + "_view_form", this.dataset, false);
        if (this.options.alternative_form_view) {
            this.view_form.set_embedded_view(this.options.alternative_form_view);
        }
        this.view_form.start();
        this.view_form.on_loaded.add_last(function() {
            var $buttons = self.view_form.$element.find(".oe_form_buttons");
            $buttons.html(QWeb.render("SelectCreatePopup.form.buttons", {widget:self}));
            var $nbutton = $buttons.find(".oe_selectcreatepopup-form-save-new");
            $nbutton.click(function() {
                self._created = $.Deferred().then(function() {
                    self._created = undefined;
                    self.view_form.on_button_new();
                });
                self.view_form.do_save();
            });
            var $nbutton = $buttons.find(".oe_selectcreatepopup-form-save");
            $nbutton.click(function() {
                self._created = $.Deferred().then(function() {
                    self._created = undefined;
                    self.check_exit();
                });
                self.view_form.do_save();
            });
            var $cbutton = $buttons.find(".oe_selectcreatepopup-form-close");
            $cbutton.click(function() {
                self.check_exit();
            });
        });
        this.dataset.on_create.add(function(data) {
            self.options.create_function(data).then(function(r) {
                self.created_elements.push(r.result);
                if (self._created) {
                    self._created.resolve();
                }
            });
        });
        this.view_form.do_show();
    },
    check_exit: function() {
        if (this.created_elements.length > 0) {
            this.on_select_elements(this.created_elements);
        }
        this.stop();
    }
});

openerp.base.form.SelectCreateListView = openerp.base.ListView.extend({
    do_add_record: function () {
        this.popup.new_object();
    },
    select_record: function(index) {
        this.popup.on_select_elements([this.dataset.ids[index]]);
        this.popup.stop();
    },
    do_select: function(ids, records) {
        this._super(ids, records);
        this.popup.on_click_element(ids);
    }
});

openerp.base.form.FormOpenPopup = openerp.base.OldWidget.extend({
    identifier_prefix: "formopenpopup",
    template: "FormOpenPopup",
    /**
     * options:
     * - alternative_form_view
     * - auto_write (default true)
     * - parent_view
     */
    show_element: function(model, row_id, context, options) {
        this.model = model;
        this.row_id = row_id;
        this.context = context || {};
        this.options = _.defaults(options || {}, {"auto_write": true});
        jQuery(this.render()).dialog({title: '',
                    modal: true,
                    width: 960,
                    height: 600});
        this.start();
    },
    start: function() {
        this._super();
        this.dataset = new openerp.base.ReadOnlyDataSetSearch(this, this.model, this.context);
        this.dataset.ids = [this.row_id];
        this.dataset.index = 0;
        this.dataset.parent_view = this.options.parent_view;
        this.setup_form_view();
    },
    on_write: function(id, data) {
        this.stop();
        if (!this.options.auto_write)
            return;
        var self = this;
        var wdataset = new openerp.base.DataSetSearch(this, this.model, this.context, this.domain);
        wdataset.parent_view = this.options.parent_view;
        wdataset.write(id, data, function(r) {
            self.on_write_completed();
        });
    },
    on_write_completed: function() {},
    setup_form_view: function() {
        var self = this;
        this.view_form = new openerp.base.FormView(this, this.element_id + "_view_form", this.dataset, false);
        if (this.options.alternative_form_view) {
            this.view_form.set_embedded_view(this.options.alternative_form_view);
        }
        this.view_form.start();
        this.view_form.on_loaded.add_last(function() {
            var $buttons = self.view_form.$element.find(".oe_form_buttons");
            $buttons.html(QWeb.render("FormOpenPopup.form.buttons"));
            var $nbutton = $buttons.find(".oe_formopenpopup-form-save");
            $nbutton.click(function() {
                self.view_form.do_save();
            });
            var $cbutton = $buttons.find(".oe_formopenpopup-form-close");
            $cbutton.click(function() {
                self.stop();
            });
            self.view_form.do_show();
        });
        this.dataset.on_write.add(this.on_write);
    }
});

openerp.base.form.FieldReference = openerp.base.form.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "FieldReference";
        this.fields_view = {
            fields: {
                selection: {
                    selection: view.fields_view.fields[this.name].selection
                },
                m2o: {
                    relation: null
                }
            }
        }
        this.get_fields_values = view.get_fields_values;
        this.do_onchange = this.on_form_changed = this.on_nop;
        this.widgets = {};
        this.fields = {};
        this.selection = new openerp.base.form.FieldSelection(this, { attrs: {
            name: 'selection',
            widget: 'selection'
        }});
        this.selection.on_value_changed.add_last(this.on_selection_changed);
        this.m2o = new openerp.base.form.FieldMany2One(this, { attrs: {
            name: 'm2o',
            widget: 'many2one'
        }});
    },
    on_nop: function() {
    },
    on_selection_changed: function() {
        this.m2o.field.relation = this.selection.get_value();
        this.m2o.set_value(null);
    },
    start: function() {
        this._super();
        this.selection.start();
        this.m2o.start();
    },
    is_valid: function() {
        return this.required === false || typeof(this.get_value()) === 'string';
    },
    is_dirty: function() {
        return this.selection.is_dirty() || this.m2o.is_dirty();
    },
    set_value: function(value) {
        this._super(value);
        if (typeof(value) === 'string') {
            var vals = value.split(',');
            this.selection.set_value(vals[0]);
            this.m2o.set_value(parseInt(vals[1], 10));
        }
    },
    get_value: function() {
        var model = this.selection.get_value(),
            id = this.m2o.get_value();
        if (typeof(model) === 'string' && typeof(id) === 'number') {
            return model + ',' + id;
        } else {
            return false;
        }
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
    update_dom: function() {
        this._super.apply(this, arguments);
        this.$element.find('.oe-binary').toggle(!this.readonly);
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
            // TODO: use openerp web crashmanager
            this.log("Error while uploading file : ", name);
        } else {
            this.on_file_uploaded_and_valid.apply(this, arguments);
            this.on_ui_change();
        }
        this.toggle_progress();
    },
    on_file_uploaded_and_valid: function(size, name, content_type, file_base64) {
    },
    on_save_as: function() {
        if (!this.view.datarecord.id) {
            this.notification.warn("Can't save file", "The record has not yet been saved");
        } else {
            var url = '/base/binary/saveas?session_id=' + this.session.session_id + '&model=' +
                this.view.dataset.model +'&id=' + (this.view.datarecord.id || '') + '&field=' + this.name +
                '&fieldname=' + (this.node.attrs.filename || '') + '&t=' + (new Date().getTime())
            window.open(url);
        }
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
    set_value: function(value) {
        this._super.apply(this, arguments);
        this.set_image_maxwidth();
        var url = '/base/binary/image?session_id=' + this.session.session_id + '&model=' +
            this.view.dataset.model +'&id=' + (this.view.datarecord.id || '') + '&field=' + this.name + '&t=' + (new Date().getTime())
        this.$image.attr('src', url);
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
    }
});

/**
 * Registry of form widgets, called by :js:`openerp.base.FormView`
 */
openerp.base.form.widgets = new openerp.base.Registry({
    'frame' : 'openerp.base.form.WidgetFrame',
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
    'integer': 'openerp.base.form.FieldInteger',
    'progressbar': 'openerp.base.form.FieldProgressBar',
    'float_time': 'openerp.base.form.FieldFloatTime',
    'image': 'openerp.base.form.FieldBinaryImage',
    'binary': 'openerp.base.form.FieldBinaryFile'
});

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
