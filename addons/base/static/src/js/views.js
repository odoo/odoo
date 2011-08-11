/*---------------------------------------------------------
 * OpenERP base library
 *---------------------------------------------------------*/

openerp.base.views = function(openerp) {

/**
 * Registry for all the client actions key: tag value: widget
 */
openerp.base.client_actions = new openerp.base.Registry();

openerp.base.ActionManager = openerp.base.Widget.extend({
    identifier_prefix: "actionmanager",
    init: function(parent) {
        this._super(parent);
        this.inner_viewmanager = null;
        this.dialog = null;
        this.dialog_viewmanager = null;
        this.client_widget = null;
    },
    render: function() {
        return "<div id='"+this.element_id+"'></div>";
    },
    dialog_stop: function () {
        if (this.dialog) {
            this.dialog_viewmanager.stop();
            this.dialog_viewmanager = null;
            this.dialog.stop();
            this.dialog = null;
        }
    },
    inner_stop: function () {
        if (this.inner_viewmanager) {
            this.inner_viewmanager.stop();
            this.inner_viewmanager = null;
        }
    },
    do_action: function(action, on_closed) {
        var type = action.type.replace(/\./g,'_');
        var popup = action.target === 'new';
        action.flags = _.extend({
            popup: popup,
            views_switcher : !popup,
            search_view : !popup,
            action_buttons : !popup,
            sidebar : !popup,
            pager : !popup
        }, action.flags || {});
        if (!(type in this)) {
            this.log("Action manager can't handle action of type " + action.type, action);
            return;
        }
        this[type](action, on_close);
    },
    ir_actions_act_window: function (action, on_close) {
        if (action.flags.popup) {
            if (this.dialog == null) {
                this.dialog = new openerp.base.Dialog(this, { title: action.name, width: '80%' });
                if(on_close)
                    this.dialog.on_close.add(on_close);
                this.dialog.start();
            } else {
                this.dialog_viewmanager.stop();
            }
            this.dialog_viewmanager = new openerp.base.ViewManagerAction(this, action);
            this.dialog_viewmanager.appendTo(this.dialog.$element);
            this.dialog.open();
        } else  {
            this.dialog_stop();
            this.inner_stop();
            this.inner_viewmanager = new openerp.base.ViewManagerAction(this, action);
            this.inner_viewmanager.appendTo(this.$element);
        }
        /* new window code
            this.rpc("/base/session/save_session_action", { the_action : action}, function(key) {
                var url = window.location.protocol + "//" + window.location.host + window.location.pathname + "?" + jQuery.param({ s_action : "" + key });
                window.open(url,'_blank');
            });
        */
    },
    ir_actions_act_window_close: function (action, on_closed) {
        this.dialog_stop();
    },
    ir_actions_server: function (action, on_closed) {
        var self = this;
        this.rpc('/base/action/run', {
            action_id: action.id,
            context: {active_id: 66, active_ids: [66], active_model: 'ir.ui.menu'}
        }).then(function (action) {
            self.do_action(action, on_closed)
        });
    },
    ir_actions_client: function (action) {
        this.client_widget = openerp.base.client_actions.get_object(action.tag);
        new this.client_widget(this, this.element_id, action.params).start();
    },
});

openerp.base.ViewManager =  openerp.base.Widget.extend({
    identifier_prefix: "viewmanager",
    init: function(parent, dataset, views) {
        this._super(parent);
        this.model = dataset.model;
        this.dataset = dataset;
        this.searchview = null;
        this.active_view = null;
        this.views_src = _.map(views, function(x) {return x instanceof Array? {view_id: x[0], view_type: x[1]} : x;});
        this.views = {};
        this.flags = this.flags || {};
        this.registry = openerp.base.views;
    },
    render: function() {
        return QWeb.render("ViewManager", {"prefix": this.element_id, views: this.views_src})
    },
    /**
     * @returns {jQuery.Deferred} initial view loading promise
     */
    start: function() {
        this._super();
        var self = this;
        this.dataset.start();
        this.$element.find('.oe_vm_switch button').click(function() {
            self.on_mode_switch($(this).data('view-type'));
        });
        var views_ids = {};
        _.each(this.views_src, function(view) {
            self.views[view.view_type] = $.extend({}, view, {
                controller : null,
                options : _.extend({
                    sidebar_id : self.element_id + '_sidebar_' + view.view_type,
                    action : self.action,
                    action_views_ids : views_ids
                }, self.flags, view.options || {})
            });
            views_ids[view.view_type] = view.view_id;
        });
        if (this.flags.views_switcher === false) {
            this.$element.find('.oe_vm_switch').hide();
        }
        // switch to the first one in sequence
        return this.on_mode_switch(this.views_src[0].view_type);
    },
    /**
     * Asks the view manager to switch visualization mode.
     *
     * @param {String} view_type type of view to display
     * @returns {jQuery.Deferred} new view loading promise
     */
    on_mode_switch: function(view_type) {
        var self = this,
            view_promise;
        this.active_view = view_type;
        var view = this.views[view_type];
        if (!view.controller) {
            // Lazy loading of views
            var controllerclass = this.registry.get_object(view_type);
            var controller = new controllerclass(this, this.element_id + '_view_' + view_type,
                this.dataset, view.view_id, view.options);
            if (view.embedded_view) {
                controller.set_embedded_view(view.embedded_view);
            }
            controller.do_switch_view.add_last(this.on_mode_switch);
            if (view_type === 'list' && this.flags.search_view === false && this.action && this.action['auto_search']) {
                // In case the search view is not instantiated: manually call ListView#search
                var domains = !_(self.action.domain).isEmpty()
                                ? [self.action.domain] : [],
                   contexts = !_(self.action.context).isEmpty()
                                ? [self.action.context] : [];
                controller.on_loaded.add({
                    callback: function () {
                        controller.do_search(domains, contexts, []);
                    },
                    position: 'last',
                    unique: true
                });
            }
            view_promise = controller.start();
            $.when(view_promise).then(function() {
                self.on_controller_inited(view_type, controller);
            });
            this.views[view_type].controller = controller;
        }


        if (this.searchview) {
            if (view.controller.searchable === false) {
                this.searchview.hide();
            } else {
                this.searchview.show();
            }
        }

        this.$element
            .find('.views-switchers button').removeAttr('disabled')
            .filter('[data-view-type="' + view_type + '"]')
            .attr('disabled', true);

        for (var view_name in this.views) {
            if (!this.views.hasOwnProperty(view_name)) { continue; }
            if (this.views[view_name].controller) {
                if (view_name === view_type) {
                    $.when(view_promise).then(this.views[view_name].controller.do_show);
                } else {
                    this.views[view_name].controller.do_hide();
                }
            }
        }
        return view_promise;
    },
    /**
     * Event launched when a controller has been inited.
     *
     * @param {String} view_type type of view
     * @param {String} view the inited controller
     */
    on_controller_inited: function(view_type, view) {
    },
    /**
     * Sets up the current viewmanager's search view.
     *
     * @param view_id the view to use or false for a default one
     * @returns {jQuery.Deferred} search view startup deferred
     */
    setup_search_view: function(view_id, search_defaults) {
        var self = this;
        if (this.searchview) {
            this.searchview.stop();
        }
        this.searchview = new openerp.base.SearchView(this, this.element_id + "_search", this.dataset, view_id, search_defaults);
        if (this.flags.search_view === false) {
            this.searchview.hide();
        }
        this.searchview.on_search.add(function(domains, contexts, groupbys) {
            var controller = self.views[self.active_view].controller;
            controller.do_search.call(controller, domains, contexts, groupbys);
        });
        return this.searchview.start();
    },
    /**
     * Called when one of the view want to execute an action
     */
    on_action: function(action) {
    },
    on_create: function() {
    },
    on_remove: function() {
    },
    on_edit: function() {
    }
});

openerp.base.ViewManagerAction = openerp.base.ViewManager.extend({
    init: function(parent, action) {
        this.session = parent.session;
        var dataset;
        if (!action.res_id) {
            dataset = new openerp.base.DataSetSearch(this, action.res_model, action.context, action.domain);
        } else {
            dataset = new openerp.base.DataSetStatic(this, action.res_model, action.context, [action.res_id]);
        }
        this.action = action;
        this._super(parent, dataset, action.views);
        this.action = action;
        this.flags = this.action.flags || {};
        if (action.res_model == 'board.board' && action.views.length == 1 && action.views) {
            // Not elegant but allows to avoid flickering of SearchView#do_hide
            this.flags.search_view = this.flags.pager = this.flags.sidebar = this.flags.action_buttons = false;
        }
    },
    start: function() {
        var inital_view_loaded = this._super();

        var search_defaults = {};
        _.each(this.action.context, function (value, key) {
            var match = /^search_default_(.*)$/.exec(key);
            if (match) {
                search_defaults[match[1]] = value;
            }
        });

        if (this.flags.search_view !== false) {
            // init search view
            var searchview_id = this.action.search_view_id && this.action.search_view_id[0];

            var searchview_loaded = this.setup_search_view(
                    searchview_id || false, search_defaults);

            // schedule auto_search
            if (searchview_loaded != null && this.action['auto_search']) {
                $.when(searchview_loaded, inital_view_loaded)
                    .then(this.searchview.do_search);
            }
        }
    }
});

openerp.base.Sidebar = openerp.base.Widget.extend({
    init: function(parent, element_id) {
        this._super(parent, element_id);
        this.items = {};
        this.sections = {};
    },
    start: function() {
        var self = this;
        this._super(this, arguments);
        this.$element.html(QWeb.render('Sidebar'));
        this.$element.find(".toggle-sidebar").click(function(e) {
            self.do_toggle();
        });
    },
    add_toolbar: function(toolbar) {
        var self = this;
        _.each([['print', "Reports"], ['action', "Actions"], ['relate', "Links"]], function(type) {
            var items = toolbar[type[0]];
            if (items.length) {
                for (var i = 0; i < items.length; i++) {
                    items[i] = {
                        label: items[i]['name'],
                        action: items[i],
                        classname: 'oe_sidebar_' + type[0]
                    }
                }
                self.add_section(type[0], type[1], items);
            }
        });
    },
    add_section: function(code, name, items) {
        // For each section, we pass a name/label and optionally an array of items.
        // If no items are passed, then the section will be created as a custom section
        // returning back an element_id to be used by a custom controller.
        // Else, the section is a standard section with items displayed as links.
        // An item is a dictonary : {
        //    label: label to be displayed for the link,
        //    action: action to be launch when the link is clicked,
        //    callback: a function to be executed when the link is clicked,
        //    classname: optional dom class name for the line,
        //    title: optional title for the link
        // }
        // Note: The item should have one action or/and a callback
        var self = this,
            section_id = _.uniqueId(this.element_id + '_section_' + code + '_');
        if (items) {
            for (var i = 0; i < items.length; i++) {
                items[i].element_id = _.uniqueId(section_id + '_item_');
                this.items[items[i].element_id] = items[i];
            }
        }
        var $section = $(QWeb.render("Sidebar.section", {
            section_id: section_id,
            name: name,
            classname: 'oe_sidebar_' + code,
            items: items
        }));
        if (items) {
            $section.find('a.oe_sidebar_action_a').click(function() {
                var item = self.items[$(this).attr('id')];
                if (item.callback) {
                    item.callback();
                }
                if (item.action) {
                    item.action.flags = item.action.flags || {};
                    item.action.flags.new_window = true;
                    self.do_action(item.action);
                }
                return false;
            });
        }
        $section.appendTo(this.$element.find('div.sidebar-actions'));
        this.sections[code] = $section;
        return section_id;
    },
    do_fold: function() {
        this.$element.addClass('closed-sidebar').removeClass('open-sidebar');
    },
    do_unfold: function() {
        this.$element.addClass('open-sidebar').removeClass('closed-sidebar');
    },
    do_toggle: function() {
        this.$element.toggleClass('open-sidebar closed-sidebar');
    }
});

openerp.base.View = openerp.base.Widget.extend({
    set_default_options: function(options) {
        this.options = options || {};
        _.defaults(this.options, {
            // All possible views options should be defaulted here
            sidebar_id: null,
            sidebar: true,
            action: null,
            action_views_ids: {}
        });
    },
    /**
     * Fetches and executes the action identified by ``action_data``.
     *
     * @param {Object} action_data the action descriptor data
     * @param {String} action_data.name the action name, used to uniquely identify the action to find and execute it
     * @param {String} [action_data.special=null] special action handlers (currently: only ``'cancel'``)
     * @param {String} [action_data.type='workflow'] the action type, if present, one of ``'object'``, ``'action'`` or ``'workflow'``
     * @param {Object} [action_data.context=null] additional action context, to add to the current context
     * @param {openerp.base.DataSet} dataset a dataset object used to communicate with the server
     * @param {Object} [record_id] the identifier of the object on which the action is to be applied
     * @param {Function} on_closed callback to execute when dialog is closed or when the action does not generate any result (no new action)
     */
    execute_action: function (action_data, dataset, record_id, on_closed) {
        var self = this;
        var handler = function (r) {
            var action = r.result;
            if (action && action.constructor == Object) {
                action.context = action.context || {};
                _.extend(action.context, {
                    active_id: record_id || false,
                    active_ids: [record_id || false],
                    active_model: dataset.model
                });
                self.do_action(action, on_closed);
            } else if (on_closed) {
                on_closed(action);
            }
        };

        var context = new openerp.base.CompoundContext(dataset.get_context(), action_data.context || {});

        if (action_data.special) {
            handler({result: {"type":"ir.actions.act_window_close"}});
        } else if (action_data.type=="object") {
            return dataset.call_button(action_data.name, [[record_id], context], handler);
        } else if (action_data.type=="action") {
            return this.rpc('/base/action/load', { action_id: parseInt(action_data.name, 10), context: context }, handler);
        } else  {
            return dataset.exec_workflow(record_id, action_data.name, handler);
        }
    },
    /**
     * Directly set a view to use instead of calling fields_view_get. This method must
     * be called before start(). When an embedded view is set, underlying implementations
     * of openerp.base.View must use the provided view instead of any other one.
     *
     * @param embedded_view A view.
     */
    set_embedded_view: function(embedded_view) {
        this.embedded_view = embedded_view;
        this.options.sidebar = false;
    },
    do_switch_view: function(view) {
    },
    set_common_sidebar_sections: function(sidebar) {
        sidebar.add_section('customize', "Customize", [
            {
                label: "Manage Views",
                callback: this.on_sidebar_manage_view,
                title: "Manage views of the current object"
            }, {
                label: "Edit Workflow",
                callback: this.on_sidebar_edit_workflow,
                title: "Manage views of the current object",
                classname: 'oe_hide oe_sidebar_edit_workflow'
            }, {
                label: "Customize Object",
                callback: this.on_sidebar_customize_object,
                title: "Manage views of the current object"
            }
        ]);
        sidebar.add_section('other', "Other Options", [
            {
                label: "Import",
                callback: this.on_sidebar_import
            }, {
                label: "Export",
                callback: this.on_sidebar_export
            }, {
                label: "Translate",
                callback: this.on_sidebar_translate,
                classname: 'oe_hide oe_sidebar_translate'
            }, {
                label: "View Log",
                callback: this.on_sidebar_view_log,
                classname: 'oe_hide oe_sidebar_view_log'
            }
        ]);
    },
    on_sidebar_manage_view: function() {
        if (this.fields_view && this.fields_view.arch) {
            $('<xmp>' + openerp.base.json_node_to_xml(this.fields_view.arch, true) + '</xmp>').dialog({ width: '95%', height: 600});
        } else {
            this.notification.warn("Manage Views", "Could not find current view declaration");
        }
    },
    on_sidebar_edit_workflow: function() {
        this.log('Todo');
    },
    on_sidebar_customize_object: function() {
        this.log('Todo');
    },
    on_sidebar_import: function() {
    },
    on_sidebar_export: function() {
        var export_view = new openerp.base.DataExport(this, this.dataset);
        export_view.start();
    },
    on_sidebar_translate: function() {
    },
    on_sidebar_view_log: function() {
    }
});

/**
 * Registry for all the main views
 */
openerp.base.views = new openerp.base.Registry();

openerp.base.json_node_to_xml = function(node, single_quote, indent) {
    // For debugging purpose, this function will convert a json node back to xml
    // Maybe usefull for xml view editor

    if (typeof(node) === 'string') {
        return node;
    }
    else if (typeof(node.tag) !== 'string' || !node.children instanceof Array || !node.attrs instanceof Object) {
        throw("Node a json node");
    }
    indent = indent || 0;
    var sindent = new Array(indent + 1).join('\t'),
        r = sindent + '<' + node.tag;
    for (var attr in node.attrs) {
        var vattr = node.attrs[attr];
        if (typeof(vattr) !== 'string') {
            // domains, ...
            vattr = JSON.stringify(vattr);
        }
        vattr = vattr.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        if (single_quote) {
            vattr = vattr.replace(/&quot;/g, "'");
        }
        r += ' ' + attr + '="' + vattr + '"';
    }
    if (node.children.length) {
        r += '>\n';
        var childs = [];
        for (var i = 0, ii = node.children.length; i < ii; i++) {
            childs.push(openerp.base.json_node_to_xml(node.children[i], single_quote, indent + 1));
        }
        r += childs.join('\n');
        r += '\n' + sindent + '</' + node.tag + '>';
        return r;
    } else {
        return r + '/>';
    }
}

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
