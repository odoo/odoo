/*---------------------------------------------------------
 * OpenERP web library
 *---------------------------------------------------------*/

openerp.web.view_tree = function(instance) {
var QWeb = instance.web.qweb,
      _lt = instance.web._lt;

instance.web.views.add('tree', 'instance.web.TreeView');
instance.web.TreeView = instance.web.View.extend(/** @lends instance.web.TreeView# */{
    display_name: _lt('Tree'),
    /**
     * Indicates that this view is not searchable, and thus that no search
     * view should be displayed (if there is one active).
     */
    searchable : false,
    /**
     * Genuine tree view (the one displayed as a tree, not the list)
     *
     * @constructs instance.web.TreeView
     * @extends instance.web.View
     *
     * @param parent
     * @param dataset
     * @param view_id
     * @param options
     */
    init: function(parent, dataset, view_id, options) {
        this._super(parent);
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;

        this.records = {};

        this.options = _.extend({}, this.defaults, options || {});

        _.bindAll(this, 'color_for');
    },

    start: function () {
        return this.rpc("/web/treeview/load", {
            model: this.model,
            view_id: this.view_id,
            view_type: "tree",
            toolbar: this.view_manager ? !!this.view_manager.sidebar : false,
            context: this.dataset.get_context()
        }, this.on_loaded);
    },
    /**
     * Returns the list of fields needed to correctly read objects.
     *
     * Gathers the names of all fields in fields_view_get, and adds the
     * field_parent (children_field in the tree view) if it's not already one
     * of the fields to fetch
     *
     * @returns {Array} an array of fields which can be provided to DataSet.read_slice and others
     */
    fields_list: function () {
        var fields = _.keys(this.fields);
        if (!_(fields).contains(this.children_field)) {
            fields.push(this.children_field);
        }
        return fields;
    },
    store_record:function(records){
        var self = this;
        _(records).each(function (record) {
            self.records[record.id] = record;
        });
    },
    on_loaded: function (fields_view) {
        var self = this;
        var has_toolbar = !!fields_view.arch.attrs.toolbar;
        // field name in OpenERP is kinda stupid: this is the name of the field
        // holding the ids to the children of the current node, why call it
        // field_parent?
        this.children_field = fields_view['field_parent'];
        this.fields_view = fields_view;
        _(this.fields_view.arch.children).each(function (field) {
            if (field.attrs.modifiers) {
                field.attrs.modifiers = JSON.parse(field.attrs.modifiers);
            }
        });
        this.fields = fields_view.fields;
        this.hook_row_click();
        this.$el.html(QWeb.render('TreeView', {
            'title': this.fields_view.arch.attrs.string,
            'fields_view': this.fields_view.arch.children,
            'fields': this.fields,
            'toolbar': has_toolbar
        }));
        this.$el.addClass(this.fields_view.arch.attrs['class']);

        this.dataset.read_slice(this.fields_list()).then(function(records) {
            self.store_record(records);
            if (!has_toolbar) {
                // WARNING: will do a second read on the same ids, but only on
                //          first load so not very important
                self.render_data({'null':records})
                self.getdata(_.pluck(records,"id"));
                return;
            }

            var $select = self.$el.find('select')
                .change(function () {
                    var $option = $(this).find(':selected');
                    self.getdata($option.val());
                });
            _(records).each(function (record) {
                self.records[record.id] = record;
                $('<option>')
                        .val(record.id)
                        .text(record.name)
                        .data('children', record[self.children_field])
                    .appendTo($select);
            });

            if (!_.isEmpty(records)) {
                $select.change();
            }
        });
        this.$el.find("#tree_view_expand").click(function(){
                self.expand_all();
        });
        this.$el.find("#tree_view_collapse").click(function(){
            self.collpase_all();
        });
        // TODO store open nodes in url ?...
        this.do_push_state({});

        if (!this.fields_view.arch.attrs.colors) {
            return;
        }
        this.colors = _(this.fields_view.arch.attrs.colors.split(';')).chain()
            .compact()
            .map(function(color_pair) {
                var pair = color_pair.split(':'),
                    color = pair[0],
                    expr = pair[1];
                return [color, py.parse(py.tokenize(expr)), expr];
            }).value();
    },
    expand_all: function(){
        var self = this;
        var tr = this.$el.find(".oe-treeview-table tbody tr[id^='treerow_']");
        _.each(tr,function(rec){
            self.showcontent($(rec).attr('data-id'),true);
        });
    },
    collpase_all: function(){
        var self = this;
        var root_tr = this.$el.find(".oe-treeview-table tbody tr[data-level='"+1+"']");
        _.each(root_tr,function(rec){
            if($(rec).hasClass('oe_open')){
                self.showcontent($(rec).attr('data-id'),false);
            }
        });
    },
    /**
     * Returns the color for the provided record in the current view (from the
     * ``@colors`` attribute)
     *
     * @param {Object} record record for the current row
     * @returns {String} CSS color declaration
     */
    color_for: function (record) {
        if (!this.colors) { return ''; }
        var context = _.extend({}, record, {
            uid: this.session.uid,
            current_date: new Date().toString('yyyy-MM-dd')
            // TODO: time, datetime, relativedelta
        });
        for(var i=0, len=this.colors.length; i<len; ++i) {
            var pair = this.colors[i],
                color = pair[0],
                expression = pair[1];
            if (py.evaluate(expression, context).toJSON()) {
                return 'color: ' + color + ';';
            }
            // TODO: handle evaluation errors
        }
        return '';
    },
    /**
     * Sets up opening a row
     */
    hook_row_click: function () {
        var self = this;
        this.$el.delegate('.treeview-td span, .treeview-tr span', 'click', function (e) {
            e.stopImmediatePropagation();
            self.activate($(this).closest('tr').data('id'));
        });

        this.$el.delegate('.treeview-tr', 'click', function () {
            var $this = $(this),
                record_id = $this.data('id'),
                bool = $this.parent().hasClass('oe_open');
                self.showcontent(record_id, !bool);
        });
    },
    // get child data of selected value
    getdata: function (id) {
        var self = this;
        var parent_child ={};
        id = _.isArray(id)?id:parseInt(id); 
        var ir_model_data = new instance.web.Model(this.model,self.dataset.get_context() || {},[['id','child_of',id]]).query();
        ir_model_data._execute().then(function(records){
              self.store_record(records);
             _.each(records,function(rec){
                 if(rec[self.children_field].length === 0)return;
                 parent_child[rec.id] = [];
                 _.each(rec[self.children_field],function(key){
                     parent_child[rec.id].push(self.records[key]);
                 });
             })
             self.render_data(parent_child);
        });
    },
    render_data: function(groupby){
        var self = this;
        _.each(_.keys(groupby),function(key){
            var $curr_node = self.$el.find('#treerow_' + key);
            var record = groupby[key];
            var children_rows = QWeb.render('TreeView.rows', {
                'records': record,
                'children_field': self.children_field,
                'fields_view': self.fields_view.arch.children,
                'fields': self.fields,
                'level': ($curr_node.data('level') || 0) + 1,
                'render': instance.web.format_value,
                'color_for': self.color_for
            });
            if ($curr_node.length) {
                $curr_node.addClass('oe_open');
                $curr_node.after(children_rows);
            } else {
                self.$el.find('tbody').html(children_rows);
            }
        });
        self.collpase_all();
    },


    // Get details in listview
    activate: function(id) {
        var self = this;
        var local_context = {
            active_model: self.dataset.model,
            active_id: id,
            active_ids: [id]};
        return this.rpc('/web/treeview/action', {
            id: id,
            model: this.dataset.model,
            context: new instance.web.CompoundContext(
                this.dataset.get_context(), local_context)
        }).pipe(function (actions) {
            if (!actions.length) { return; }
            var action = actions[0][2];
            var c = new instance.web.CompoundContext(local_context);
            if (action.context) {
                c.add(action.context);
            }
            return self.rpc('/web/session/eval_domain_and_context', {
                contexts: [c], domains: []
            }).pipe(function (res) {
                action.context = res.context;
                return self.do_action(action);
            }, null);
        }, null);
    },

    // show & hide the contents
    showcontent: function (record_id, show) {
        this.$el.find('#treerow_' + record_id)
                .toggleClass('oe_open', show);

        _(this.records[record_id][this.children_field]).each(function (child_id) {
            var $child_row = this.$el.find('#treerow_' + child_id);
            if ($child_row.hasClass('oe_open')) {
                this.showcontent(child_id, false);
            }
            $child_row.toggle(show);
        }, this);
    },

});
};
