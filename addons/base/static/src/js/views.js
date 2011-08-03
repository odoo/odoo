/*---------------------------------------------------------
 * OpenERP base library
 *---------------------------------------------------------*/

openerp.base.views = function(openerp) {

openerp.base.ActionManager = openerp.base.Widget.extend({
// process all kind of actions
    init: function(parent, element_id) {
        this._super(parent, element_id);
        this.viewmanager = null;
        this.current_dialog = null;
        // Temporary linking view_manager to session.
        // Will use parent to find it when implementation will be done.
        this.session.action_manager = this;
    },
    /**
     * Process an action
     * Supported actions: act_window
     */
    action_window: function() {
    },
    action_window_close: function() {
    },
    action_server: function() {
    },
    action_url: function() {
    },
    action_report: function() {
    },
    action_client: function() {
    },
    do_action: function(action, on_closed) {
        var self = this;
        action.flags = _.extend({
            sidebar : action.target != 'new',
            search_view : action.target != 'new',
            new_window : false,
            views_switcher : action.target != 'new',
            action_buttons : action.target != 'new',
            pager : action.target != 'new'
        }, action.flags || {});
        // instantiate the right controllers by understanding the action
        switch (action.type) {
            case 'ir.actions.act_window':
                if (!action.target && this.current_dialog) {
                    action.flags.new_window = true;
                }
                if (action.target == 'new') {
                    var dialog = this.current_dialog = new openerp.base.ActionDialog(this, { title: action.name, width: '90%' });
                    if (on_closed) {
                        dialog.close_callback = on_closed;
                    }
                    dialog.start(false);
                    var viewmanager = dialog.viewmanager = new openerp.base.ViewManagerAction(this, dialog.element_id, action);
                    viewmanager.start();
                    dialog.open();
                } else if (action.flags.new_window) {
                    action.flags.new_window = false;
                    this.rpc("/base/session/save_session_action", { the_action : action}, function(key) {
                        var url = window.location.protocol + "//" + window.location.host +
                                window.location.pathname + "?" + jQuery.param({ s_action : "" + key });
                        window.open(url);
                        if (on_closed) {
                            on_closed();
                        }
                    });
                } else {
                    if (this.viewmanager) {
                        this.viewmanager.stop();
                    }
                    this.viewmanager = new openerp.base.ViewManagerAction(this, this.element_id, action);
                    this.viewmanager.start();
                }
                break;
            case 'ir.actions.act_window_close':
                this.close_dialog();
                break;
            case 'ir.actions.server':
                this.rpc('/base/action/run', {
                    action_id: action.id,
                    context: {active_id: 66, active_ids: [66], active_model: 'ir.ui.menu'}
                }).then(function (action) {
                    self.do_action(action, on_closed)
                });
                break;
            default:
                console.log("Action manager can't handle action of type " + action.type, action);
        }
    },
    close_dialog: function() {
        if (this.current_dialog) {
            this.current_dialog.stop();
            this.current_dialog = null;
        }
    }
});

openerp.base.ActionDialog = openerp.base.Dialog.extend({
    identifier_prefix: 'action_dialog',
    on_close: function() {
        this._super(this, arguments);
        if (this.close_callback) {
            this.close_callback();
        }
    },
    stop: function() {
        this._super(this, arguments);
        if (this.viewmanager) {
            this.viewmanager.stop();
        }
    }
});

openerp.base.ViewManager =  openerp.base.Widget.extend({
    init: function(parent, element_id, dataset, views) {
        this._super(parent, element_id);
        this.model = dataset.model;
        this.dataset = dataset;
        this.searchview = null;
        this.active_view = null;
        this.views_src = _.map(views, function(x)
            {return x instanceof Array? {view_id: x[0], view_type: x[1]} : x;});
        this.views = {};
        this.flags = this.flags || {};
        this.registry = openerp.base.views;
    },
    /**
     * @returns {jQuery.Deferred} initial view loading promise
     */
    start: function() {
        this._super();
        var self = this;
        this.dataset.start();
        this.$element.html(QWeb.render("ViewManager", {"prefix": this.element_id, views: this.views_src}));
        this.$element.find('.oe_vm_switch button').click(function() {
            self.on_mode_switch($(this).data('view-type'));
        });
        _.each(this.views_src, function(view) {
            self.views[view.view_type] = $.extend({}, view, {
                controller : null,
                options : _.extend({
                    sidebar_id : self.element_id + '_sidebar_' + view.view_type
                }, self.flags)
            });
        });
        if (this.flags.views_switcher === false) {
            this.$element.find('.oe_vm_switch').hide();
        }
        // switch to the first one in sequence
        return this.on_mode_switch(this.views_src[0].view_type);
    },
    stop: function() {
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
    on_controller_inited: function(view_type, view) {},
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
            self.views[self.active_view].controller.do_search.call(
                self, domains.concat(self.domains()),
                      contexts.concat(self.contexts()), groupbys);
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
    },
    /**
     * Domains added on searches by the view manager, to override in subsequent
     * view manager in order to add new pieces of domains to searches
     *
     * @returns an empty list
     */
    domains: function () {
        return [];
    },
    /**
     * Contexts added on searches by the view manager.
     *
     * @returns an empty list
     */
    contexts: function () {
        return [];
    }
});

openerp.base.NullViewManager = openerp.base.generate_null_object_class(openerp.base.ViewManager, {
    init: function(parent) {
        this._super(parent);
        if(parent)
            this.session = parent.session;
        this.action = {flags: {}};
    }
});

// TODO Will move to action Manager
openerp.base.ViewManagerAction = openerp.base.ViewManager.extend({
    init: function(parent, element_id, action) {
        this.session = parent.session;
        var dataset;
        if (!action.res_id) {
            dataset = new openerp.base.DataSetSearch(this, action.res_model, action.context || null);
        } else {
            dataset = new openerp.base.DataSetStatic(this, action.res_model, {}, [action.res_id]);
            if (action.context) {
                // TODO fme: should normalize all DataSets constructors to (session, model, context, ...)
                dataset.context = action.context;
            }
        }
        this._super(parent, element_id, dataset, action.views);
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
    },
    stop: function() {
        // should be replaced by automatic destruction implemented in Widget
        this._super();
    },
    /**
     * adds action domain to the search domains
     *
     * @returns the action's domain
     */
    domains: function () {
        if (!this.action.domain) {
            return [];
        }
        return [this.action.domain];
    },
    /**
     * adds action context to the search contexts
     *
     * @returns the action's context
     */
    contexts: function () {
        if (!this.action.context) {
            return [];
        }
        return [this.action.context];
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
            sidebar: true
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
     * @param {openerp.base.ActionManager} action_manager object able to actually execute the action, if any is fetched
     * @param {Object} [record_id] the identifier of the object on which the action is to be applied
     * @param {Function} on_closed callback to execute when dialog is closed or when the action does not generate any result (no new action)
     */
    execute_action: function (action_data, dataset, action_manager, record_id, on_closed) {
        var self = this;
        if (action_manager.current_dialog) {
            on_closed = action_manager.current_dialog.close_callback;
        }
        var handler = function (r) {
            action_manager.close_dialog();
            var action = r.result;
            if (action && action.constructor == Object) {
                action.context = action.context || {};
                _.extend(action.context, {
                    active_id: record_id || false,
                    active_ids: [record_id || false],
                    active_model: dataset.model
                });
                action.flags = {
                    new_window: true
                };
                action_manager.do_action(action, on_closed);
            } else if (on_closed) {
                on_closed(action);
            }
        };

        if (!action_data.special) {
            var context = new openerp.base.CompoundContext(dataset.get_context(), action_data.context || {});
            switch(action_data.type) {
                case 'object':
                    return dataset.call_button(action_data.name, [[record_id], context], handler);
                case 'action':
                    return this.rpc('/base/action/load', { action_id: parseInt(action_data.name, 10), context: context }, handler);
                default:
                    return dataset.exec_workflow(record_id, action_data.name, handler);
            }
        } else {
            action_manager.close_dialog();
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
        console.log('Todo');
    },
    on_sidebar_edit_workflow: function() {
        console.log('Todo');
    },
    on_sidebar_customize_object: function() {
        console.log('Todo');
    },
    on_sidebar_import: function() {
        var import_view = new openerp.base.DataImport(this, this.dataset);
        import_view.start(false);
    },
    on_sidebar_export: function() {
        var export_view = new openerp.base.DataExport(this, this.dataset);
        export_view.start(false);
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
    if (typeof(node.tag) !== 'string' || !node.children instanceof Array || !node.attrs instanceof Object) {
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
