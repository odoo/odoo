odoo.define('web.TreeView', function (require) {
"use strict";
/*---------------------------------------------------------
 * Odoo Tree view
 *---------------------------------------------------------*/

var core = require('web.core');
var data = require('web.data');
var formats = require('web.formats');
var pyeval = require('web.pyeval');
var session = require('web.session');
var View = require('web.View');

var _lt = core._lt;
var QWeb = core.qweb;

var TreeView = View.extend(/** @lends instance.web.TreeView# */{
    display_name: _lt('Tree'),
    icon: 'fa-align-left',
    view_type: 'tree',
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

    view_loading: function(r) {
        return this.load_tree(r);
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
    load_tree: function (fields_view) {
        var self = this;
        var has_toolbar = !!fields_view.arch.attrs.toolbar;
        // field name in OpenERP is kinda stupid: this is the name of the field
        // holding the ids to the children of the current node, why call it
        // field_parent?
        this.children_field = fields_view.field_parent;
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

        this.dataset.read_slice(this.fields_list()).done(function(records) {
            if (!has_toolbar) {
                // WARNING: will do a second read on the same ids, but only on
                //          first load so not very important
                self.getdata(null, _(records).pluck('id'));
                return;
            }

            var $select = self.$el.find('select')
                .change(function () {
                    var $option = $(this).find(':selected');
                    self.getdata($option.val(), $option.data('children'));
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
            uid: session.uid,
            current_date: moment().format('YYYY-MM-DD')
            // TODO: time, datetime, relativedelta
        });
        for(var i=0, len=this.colors.length; i<len; ++i) {
            var pair = this.colors[i],
                color = pair[0],
                expression = pair[1];
            if (py.PY_isTrue(py.evaluate(expression, context))) {
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
            var is_loaded = 0,
                $this = $(this),
                record_id = $this.data('id'),
                row_parent_id = $this.data('row-parent-id'),
                record = self.records[record_id],
                children_ids = record[self.children_field];

            _(children_ids).each(function(childid) {
                if (self.$el.find('[id=treerow_' + childid + '][data-row-parent-id='+ record_id +']').length ) {
                    if (self.$el.find('[id=treerow_' + childid + '][data-row-parent-id='+ record_id +']').is(':hidden')) {
                        is_loaded = -1;
                    } else {
                        is_loaded++;
                    }
                }
            });
            if (is_loaded === 0) {
                if (!$this.parent().hasClass('oe_open')) {
                    self.getdata(record_id, children_ids);
                }
            } else {
                self.showcontent($this, record_id, is_loaded < 0);
            }
        });
    },
    // get child data of selected value
    getdata: function (id, children_ids) {
        var self = this;

        self.dataset.read_ids(children_ids, this.fields_list()).done(function(records) {
            _(records).each(function (record) {
                self.records[record.id] = record;
            });
            var $curr_node = self.$el.find('#treerow_' + id);
            var children_rows = QWeb.render('TreeView.rows', {
                'records': records,
                'children_field': self.children_field,
                'fields_view': self.fields_view.arch.children,
                'fields': self.fields,
                'level': $curr_node.data('level') || 0,
                'render': formats.format_value,
                'color_for': self.color_for,
                'row_parent_id': id
            });
            if ($curr_node.length) {
                $curr_node.addClass('oe_open');
                $curr_node.after(children_rows);
            } else {
                self.$el.find('tbody').html(children_rows);
            }
        });
    },

    // Get details in listview
    activate: function(id) {
        var self = this;
        var local_context = {
            active_model: self.dataset.model,
            active_id: id,
            active_ids: [id]
        };
        var ctx = pyeval.eval(
            'context', new data.CompoundContext(
                this.dataset.get_context(), local_context));
        return this.rpc('/web/treeview/action', {
            id: id,
            model: this.dataset.model,
            context: ctx
        }).then(function (actions) {
            if (!actions.length) { return; }
            var action = actions[0][2];
            var c = new data.CompoundContext(local_context).set_eval_context(ctx);
            if (action.context) {
                c.add(action.context);
            }
            action.context = c;
            return self.do_action(action);
        });
    },

    // show & hide the contents
    showcontent: function (curnode,record_id, show) {
        curnode.parent('tr').toggleClass('oe_open', show);
        _(this.records[record_id][this.children_field]).each(function (child_id) {
            var $child_row = this.$el.find('[id=treerow_' + child_id + '][data-row-parent-id='+ curnode.data('id') +']');
            if ($child_row.hasClass('oe_open')) {
                $child_row.toggleClass('oe_open',show);
                this.showcontent($child_row, child_id, false);
            }
            $child_row.toggle(show);
        }, this);
    },

    do_hide: function () {
        this.hidden = true;
        this._super();
    }
});

core.view_registry.add('tree', TreeView);

return TreeView;

});

