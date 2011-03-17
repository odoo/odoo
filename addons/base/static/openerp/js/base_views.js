/*---------------------------------------------------------
 * OpenERP base library
 *---------------------------------------------------------*/

openerp.base$views = function(openerp) {
openerp.base.DataSet =  openerp.base.Controller.extend({
    init: function(session, element_id, model) {
        this._super(session, element_id);
        this.model = model;
        this.model_fields = null;
        this.fields = [];
        // SHOULD USE THE ONE FROM FIELDS VIEW GET BECAUSE OF SELECTION
        this.domain = [];
        this.context = {};
        this.order = "";
        this.count = null;
        this.ids = [];
        this.values = {};
/*
    group_by
        rows record
            fields of row1 field fieldname
                { type: value: text: text_format: text_completions type_*: a
*/
    },
    start: function() {
        this.rpc("/base/dataset/fields", {"model":this.model}, this.on_fields);
    },
    on_fields: function(result) {
        this.model_fields = result.fields;
        this.on_ready();
    },
    do_load: function(offset, limit) {
        this.rpc("/base/dataset/load", {model: this.model, fields: this.fields }, this.on_loaded);
    },
    on_loaded: function(data) {
        this.ids = data.ids;
        this.values = data.values;
    },
    on_reloaded: function(ids) {
    }
});

openerp.base.DataRecord =  openerp.base.Controller.extend({
    init: function(session, element_id, model, id) {
        this._super(session, element_id);
        this.model = model;
        this.id = id;
        this.value = {};
    },
    start: function() {
    },
    on_ready: function() {
    },
    on_change: function() {
    },
    on_reload: function() {
    }
});

openerp.base.Widget = openerp.base.Controller.extend({
    init: function(session, element_id, view, node) {
        var type = view.fields_view.fields[node.attrs.name] || {};
        this.type = node.attrs.widget || type.type || node.tag;
        this.name = node.attrs.name;
        var type = view.fields_view.fields[node.attrs.name] || {};
        this.type = node.attrs.widget || type.type || node.tag;
        this.element_id = (node.tag == this.type ? node.tag : node.tag + '_' + this.type) + '_';
        this.element_id += (this.name ? this.name + (this.is_field_label ? '_label' : '') + '_' : '');
        this.element_id += Math.round(Math.random() * (new Date()).getTime());
        this._super(session, this.element_id);
        this.view = view;
        this.view.widgets[this.element_id] = this;
        this.node = node;
        this.children = node.children;
        this.colspan = parseInt(node.attrs.colspan || 1);
        if (node.tag == 'field') {
            this.view.fields[node.attrs.name] = this;
            if (node.attrs.nolabel != '1' && this.colspan > 1) {
                this.colspan--;
            }
        }
        this.field = view.fields_view.fields[node.attrs.name];
        this.template = "FormView.widget";

        this.invisible = (node.attrs.invisible == '1');
        this.string = node.attrs.string || (this.field ? this.field.string : undefined);
        this.help = node.attrs.help || (this.field ? this.field.help : undefined);
        this.nolabel = (node.attrs.nolabel == '1');
    },
    register: function() {
        this.$element = $('#' + this.element_id);
        return this;
    },
    render: function() {
        var template = this.template;
        return QWeb.render(template, { "widget": this });
    }
});

openerp.base.WidgetFrame = openerp.base.Widget.extend({
    init: function(session, element_id, view, node) {
        this._super(session, element_id, view, node);
        this.template = "FormView.frame";
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
            var widget = new openerp.base.widgets[widget_type](this.session, null, this.view, n);
            if (n.tag == 'field' && n.attrs.nolabel != '1') {
                var label = new openerp.base.widgets['label'](this.session, null, this.view, n);
                label["for"] = widget;
                this.add_widget(label);
            }
            this.add_widget(widget);
        } else {
            console.log("Unhandled widget type : " + widget_type, n);
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
    init: function(session, element_id, view, node) {
        this._super(session, element_id, view, node);
        this.template = "FormView.notebook";
        this.pages = [];
        for (var i = 0; i < node.children.length; i++) {
            var n = node.children[i];
            if (n.tag == "page") {
                var page = new openerp.base.WidgetFrame(this.session, null, this.view, n);
                this.pages.push(page);
            }
        }
    }
});

openerp.base.WidgetSeparator = openerp.base.Widget.extend({
    init: function(session, element_id, view, node) {
        this._super(session, element_id, view, node);
        this.template = "FormView.separator";
    }
});

openerp.base.WidgetLabel = openerp.base.Widget.extend({
    init: function(session, element_id, view, node) {
        this.is_field_label = true;
        this._super(session, element_id, view, node);
        this.template = "FormView.label";
        this.colspan = 1;
    }
});

openerp.base.WidgetButton = openerp.base.Widget.extend({
    init: function(session, element_id, view, node) {
        this._super(session, element_id, view, node);
        this.template = "FormView.button";
    }
});

openerp.base.Field = openerp.base.Widget.extend({
    init: function(session, element_id, view, node) {
        this._super(session, element_id, view, node);
    }
});

openerp.base.FieldChar = openerp.base.Field.extend({
    init: function(session, element_id, view, node) {
        this._super(session, element_id, view, node);
        this.template = "FormView.field.char";
    }
});

openerp.base.FieldEmail = openerp.base.Field.extend({
    init: function(session, element_id, view, node) {
        this._super(session, element_id, view, node);
        this.template = "FormView.field.char";
    }
});

openerp.base.FieldFloat = openerp.base.Field.extend({
    init: function(session, element_id, view, node) {
        this._super(session, element_id, view, node);
        this.template = "FormView.field.char";
    }
});

openerp.base.FieldBoolean = openerp.base.Field.extend({
    init: function(session, element_id, view, node) {
        this._super(session, element_id, view, node);
        this.template = "FormView.field.boolean";
    }
});

openerp.base.FieldDate = openerp.base.Field.extend({
    init: function(session, element_id, view, node) {
        this._super(session, element_id, view, node);
        this.template = "FormView.field.date";
    }
});

openerp.base.FieldDatetime = openerp.base.Field.extend({
    init: function(session, element_id, view, node) {
        this._super(session, element_id, view, node);
        this.template = "FormView.field.datetime";
    }
});

openerp.base.FieldText = openerp.base.Field.extend({
    init: function(session, element_id, view, node) {
        this._super(session, element_id, view, node);
        this.template = "FormView.field.text";
    }
});

openerp.base.FieldTextXml = openerp.base.Field.extend({
// to replace view editor
});

openerp.base.FieldSelection = openerp.base.Field.extend({
    init: function(session, element_id, view, node) {
        this._super(session, element_id, view, node);
        this.template = "FormView.field.selection";
    }
});

openerp.base.FieldMany2One = openerp.base.Field.extend({
    init: function(session, element_id, view, node) {
        this._super(session, element_id, view, node);
        this.template = "FormView.field.many2one";
    }
});

openerp.base.FieldOne2Many = openerp.base.Field.extend({
    init: function(session, element_id, view, node) {
        this._super(session, element_id, view, node);
        this.template = "FormView.field.one2many";
    }
});

openerp.base.FieldMany2Many = openerp.base.Field.extend({
    init: function(session, element_id, view, node) {
        this._super(session, element_id, view, node);
        this.template = "FormView.field.one2many";
    }
});

openerp.base.FieldReference = openerp.base.Field.extend({
    init: function(session, element_id, view, node) {
        this._super(session, element_id, view, node);
        this.template = "FormView.field.reference";
    }
});

openerp.base.widgets = {
    'group' : openerp.base.WidgetFrame,
    'notebook' : openerp.base.WidgetNotebook,
    'separator' : openerp.base.WidgetSeparator,
    'label' : openerp.base.WidgetLabel,
    'char' : openerp.base.FieldChar,
    'email' : openerp.base.FieldEmail,
    'date' : openerp.base.FieldDate,
    'datetime' : openerp.base.FieldDatetime,
    'text' : openerp.base.FieldText,
    'selection' : openerp.base.FieldSelection,
    'many2one' : openerp.base.FieldMany2One,
    'one2many' : openerp.base.FieldOne2Many,
    'reference' : openerp.base.FieldReference,
    'boolean' : openerp.base.FieldBoolean,
    'float' : openerp.base.FieldFloat,
    'button' : openerp.base.WidgetButton
}

openerp.base.FormView =  openerp.base.Controller.extend({
    init: function(session, element_id, dataset, view_id) {
        this._super(session, element_id);
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;
        this.widgets = {};
        this.fields = {};
    },
    start: function() {
        //this.log('Starting FormView '+this.model+this.view_id)
        this.rpc("/base/formview/load", {"model": this.model, "view_id": this.view_id}, this.on_loaded);
    },
    on_loaded: function(data) {
        this.fields_view = data.fields_view;
        //this.log(this.fields_view);
        var frame = new openerp.base.WidgetFrame(this.session, null, this, this.fields_view.arch);
        this.$element.html(QWeb.render("FormView", { "frame": frame, "view": this }));
        for (var i in this.widgets) {
            this.widgets[i].register();
        }
    },
    on_button: function() {
    },
    on_write: function() {
    }
});

openerp.base.ListView = openerp.base.Controller.extend({
    init: function(session, element_id, dataset, view_id) {
        this._super(session, element_id);
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;
        this.name = "";

        this.cols = [];

        this.$table = null;
        this.colnames = [];
        this.colmodel = [];

        this.event_loading = false; // TODO in the future prevent abusive click by masking
    },
    start: function() {
        //this.log('Starting ListView '+this.model+this.view_id)
        this.rpc("/base/listview/load", {"model": this.model, "view_id":this.view_id}, this.on_loaded);
    },
    on_loaded: function(data) {
        this.fields_view = data.fields_view;
        //this.log(this.fields_view);
        this.name = "" + this.fields_view.arch.attrs.string;
        this.$element.html(QWeb.render("ListView", {"fields_view": this.fields_view}));
        this.$table = this.$element.find("table");
        this.cols = [];
        this.colnames = [];
        this.colmodel = [];
        // TODO uss a object for each col, fill it with view and fallback to dataset.model_field
        var tree = this.fields_view.arch.children;
        for(var i = 0; i < tree.length; i++)  {
            var col = tree[i];
            if(col.tag == "field") {
                this.cols.push(col.attrs.name);
                this.colnames.push(col.attrs.name);
                this.colmodel.push({ name: col.attrs.name, index: col.attrs.name });
            }
        }
        //this.log(this.cols);
        this.dataset.fields = this.cols;
        this.dataset.on_loaded.add_last(this.do_fill_table);
    },
    do_fill_table: function() {
        //this.log("do_fill_table");
        
        var self = this;
        //this.log(this.dataset.data);
        var rows = [];
        var ids = this.dataset.ids;
        for(var i = 0; i < ids.length; i++)  {
            // TODO very strange is sometimes non existing ? even as admin ? example ir.ui.menu
            var row = this.dataset.values[ids[i]];
            if(row)
                rows.push(row);
//            else
//              debugger;
        }
        //this.log(rows);
        this.$table.jqGrid({
            data: rows,
            datatype: "local",
            height: "100%",
            rowNum: 100,
            //rowList: [10,20,30],
            colNames: this.colnames,
            colModel: this.colmodel,
            //pager: "#plist47",
            viewrecords: true,
            caption: this.name
        }).setGridWidth(this.$element.width());
        $(window).bind('resize', function() { self.$table.setGridWidth(self.$element.width()); }).trigger('resize');
    }
});

openerp.base.TreeView = openerp.base.Controller.extend({
});

openerp.base.CalendarView = openerp.base.Controller.extend({
// Dhtmlx scheduler ?
});

openerp.base.GanttView = openerp.base.Controller.extend({
// Dhtmlx gantt ?
});

openerp.base.DiagramView = openerp.base.Controller.extend({
// 
});

openerp.base.GraphView = openerp.base.Controller.extend({
});

openerp.base.SearchViewInput = openerp.base.Controller.extend({
// TODO not sure should we create a controller for every input ?

// of we just keep a simple dict for each input in
// openerp.base.SearchView#input_ids
// and use if when we get an event depending on the type
// i think it's less bloated to avoid useless controllers

// but i think for many2one a controller would be nice
// so simple dict for simple inputs
// an controller for many2one ?

});

openerp.base.SearchView = openerp.base.Controller.extend({
    init: function(session, element_id, dataset, view_id) {
        this._super(session, element_id);
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;
        this.input_index = 0;
        this.input_ids = {};
        this.domain = [];
    },
    start: function() {
        //this.log('Starting SearchView '+this.model+this.view_id)
        this.rpc("/base/searchview/load", {"model": this.model, "view_id":this.view_id}, this.on_loaded);
    },
    on_loaded: function(data) {
        this.fields_view = data.fields_view;
        this.log(this.fields_view);
        this.input_ids = {};
        this.$element.html(QWeb.render("SearchView", {"fields_view": this.fields_view}));
        this.$element.find("#search").bind('click',this.on_search);
        // TODO bind click event on all button
        // TODO we don't do many2one yet, but in the future bind a many2one controller on them
        this.log(this.$element.find("#search"));
    },
    register_input: function(node) {
        // self should be passed in the qweb dict to do:
        // <input t-add-id="self.register_input(node)"/>

        // generate id
        var id = this.element_id + "_" + this.input_index++;
        // TODO construct a nice object
        // save it in our registry
        this.input_ids[id] = {
            node: node,
            type: "filter",
            domain: "",
            context: "",
            disabled: false
        };

        return id;
    },
    on_click: function() {
        // event catched on a button
        // flip the disabled flag
        // adjust the css class
    },
    on_search: function() {
        this.log("on_search");
        // collect all non disabled domains definitions, AND them
        // evaluate as python expression
        // save the result in this.domain
    },
    on_clear: function() {
    }
});

openerp.base.ProcessView = openerp.base.Controller.extend({
});

openerp.base.HelpView = openerp.base.Controller.extend({
});

openerp.base.View = openerp.base.Controller.extend({
// to replace Action
});

openerp.base.Action =  openerp.base.Controller.extend({
    init: function(session, element_id) {
        this._super(session, element_id);
        this.action = null;
        this.dataset = null;
        this.searchview_id = false;
        this.searchview = null;
        this.listview_id = false;
        this.listview = null;
        this.formview_id = false;
        this.formview = null;
    },
    start: function() {
        this.$element.html(QWeb.render("Action", {"prefix":this.element_id}));
        this.$element.find("#mode_list").bind('click',this.on_mode_list);
        this.$element.find("#mode_form").bind('click',this.on_mode_form);
        this.on_mode_list();
    },
    on_mode_list: function() {
        $("#oe_action_form").hide();
        $("#oe_action_search").show();
        $("#oe_action_list").show();
    },
    on_mode_form: function() {
        $("#oe_action_form").show();
        $("#oe_action_search").hide();
        $("#oe_action_list").hide();
    },
    do_action: function(action) {
        // instantiate the right controllers by understanding the action
        this.action = action;
        this.log(action);
//        debugger;
        //this.log(action);
        if(action.type == "ir.actions.act_window") {
            this.do_action_window(action);
        }
    },
    do_action_window: function(action) {
        this.formview_id = false;
        this.dataset = new openerp.base.DataSet(this.session, "oe_action_dataset", action.res_model);
        this.dataset.start();

        // Locate first tree view
        this.listview_id = false;
        for(var i = 0; i < action.views.length; i++)  {
            if(action.views[i][1] == "tree") {
                this.listview_id = action.views[i][0];
                break;
            }
        }
        this.listview = new openerp.base.ListView(this.session, "oe_action_list", this.dataset, this.listview_id);
        this.listview.start();

        // Locate first form view
        this.listview_id = false;
        for(var j = 0; j < action.views.length; j++)  {
            if(action.views[j][1] == "form") {
                this.formview_id = action.views[j][0];
                break;
            }
        }
        this.formview = new openerp.base.FormView(this.session, "oe_action_form", this.dataset, this.formview_id);
        this.formview.start();

        // Take the only possible search view. Is that consistent ?
        this.searchview_id = false;
        if(this.listview && action.search_view_id) {
            this.searchview_id = action.search_view_id[0];
        }
        this.searchview = new openerp.base.SearchView(this.session, "oe_action_search", this.dataset, this.searchview_id);
        this.searchview.start();

        // Connect the the dataset load event with the search button of search view
        // THIS IS COOL
        this.searchview.on_search.add_last(this.dataset.do_load);
    }
});
};

// DEBUG_RPC:rpc.request:('execute', 'addons-dsh-l10n_us', 1, '*', ('ir.filters', 'get_filters', u'res.partner'))
// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
