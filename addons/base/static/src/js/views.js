/*---------------------------------------------------------
 * OpenERP base library
 *---------------------------------------------------------*/

openerp.base.views = function(openerp) {

openerp.base.ActionManager = openerp.base.Controller.extend({
// process all kind of actions
    init: function(session, element_id) {
        this._super(session, element_id);
        this.viewmanager = null;
        this.dialog_stack = [];
        // Temporary linking view_manager to session.
        // Will use controller_parent to find it when implementation will be done.
        session.action_manager = this;
    },
    /**
     * Process an action
     * Supported actions: act_window
     */
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
                if (!action.target && this.dialog_stack.length) {
                    action.flags.new_window = true;
                }
                if (action.target == 'new') {
                    var element_id = _.uniqueId("act_window_dialog");
                    $('<div>', {id: element_id}).dialog({
                        title: action.name,
                        modal: true,
                        width: '50%',
                        height: 'auto'
                    }).bind('dialogclose', function(event) {
                        // When dialog is closed with ESC key or close manually, branch to act_window_close logic
                        self.do_action({ type: 'ir.actions.act_window_close' });
                    });
                    var viewmanager = new openerp.base.ViewManagerAction(this.session, element_id, action);
                    viewmanager.start();
                    viewmanager.on_act_window_closed.add(on_closed);
                    viewmanager.is_dialog = true;
                    this.dialog_stack.push(viewmanager);
                } else if (action.flags.new_window) {
                    action.flags.new_window = false;
                    this.rpc("/base/session/save_session_action", { the_action : action}, function(key) {
                        var url = window.location.protocol + "//" + window.location.host +
                                window.location.pathname + "?" + jQuery.param({ s_action : "" + key });
                        window.open(url);
                    });
                } else {
                    if (this.viewmanager) {
                        this.viewmanager.stop();
                    }
                    this.viewmanager = new openerp.base.ViewManagerAction(this.session, this.element_id, action);
                    this.viewmanager.start();
                }
                break;
            case 'ir.actions.act_window_close':
                var dialog = this.dialog_stack.pop();
                if (!action.special) {
                    dialog.on_act_window_closed();
                }
                dialog.$element.dialog('destroy');
                dialog.stop();
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
    }
});

openerp.base.ViewManager =  openerp.base.Controller.extend({
    init: function(session, element_id, dataset, views) {
        this._super(session, element_id);
        this.model = dataset.model;
        this.dataset = dataset;
        this.searchview = null;
        this.active_view = null;
        this.views_src = _.map(views, function(x)
            {return x instanceof Array? {view_id: x[0], view_type: x[1]} : x;});
        this.views = {};
        this.flags = this.flags || {};
        this.sidebar = new openerp.base.NullSidebar();
        this.registry = openerp.base.views;
        this.is_dialog = false;
    },
    /**
     * @returns {jQuery.Deferred} initial view loading promise
     */
    start: function() {
        var self = this;
        this.dataset.start();
        this.$element.html(QWeb.render("ViewManager", {"prefix": this.element_id, views: this.views_src}));
        this.$element.find('.oe_vm_switch button').click(function() {
            self.on_mode_switch($(this).data('view-type'));
        });
        _.each(this.views_src, function(view) {
            self.views[view.view_type] = $.extend({}, view, {controller: null});
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
            var controller = new controllerclass( this, this.session, this.element_id + "_view_" + view_type,
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
        this.searchview = new openerp.base.SearchView(this, this.session, this.element_id + "_search", this.dataset, view_id, search_defaults);
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
     * Called when this view manager has been created by an action 'act_window@target=new' is closed
     */
    on_act_window_closed : function() {
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
    init: function() {
        this._super();
        this.action = {flags: {}};
        this.sidebar = new openerp.base.NullSidebar();
    }
});

openerp.base.ViewManagerAction = openerp.base.ViewManager.extend({
    init: function(session, element_id, action) {
        var dataset;
        if (!action.res_id) {
            dataset = new openerp.base.DataSetSearch(session, action.res_model, action.context || null, action.domain || null);
        } else {
            dataset = new openerp.base.DataSetStatic(session, action.res_model, {}, [action.res_id]);
            if (action.context) {
                // TODO fme: should normalize all DataSets constructors to (session, model, context, domain, ...)
                dataset.context = action.context;
            }
        }
        this._super(session, element_id, dataset, action.views);
        this.action = action;
        this.flags = this.action.flags || {};
        if (action.res_model == 'board.board' && action.views.length == 1 && action.views) {
            // Not elegant but allows to avoid flickering of SearchView#do_hide
            this.flags.search_view = this.flags.pager = this.flags.sidebar = this.flags.action_buttons = false;
        }
        if (this.flags.sidebar) {
            this.sidebar = new openerp.base.Sidebar(null, this);
        }
    },
    start: function() {
        var inital_view_loaded = this._super();

        // init sidebar
        if (this.flags.sidebar) {
            this.$element.find('.view-manager-main-sidebar').html(this.sidebar.render());
            this.sidebar.start();
        }

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
        // should be replaced by automatic destruction implemented in BaseWidget
        this.sidebar.stop();
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

openerp.base.Sidebar = openerp.base.BaseWidget.extend({
    template: "ViewManager.sidebar",
    init: function(parent, view_manager) {
        this._super(parent, view_manager.session);
        this.view_manager = view_manager;
        this.sections = [];
    },
    set_toolbar: function(toolbar) {
        this.sections = [];
        var self = this;
        _.each([["print", "Reports"], ["action", "Actions"], ["relate", "Links"]], function(type) {
            if (toolbar[type[0]].length == 0)
                return;
            var section = {elements:toolbar[type[0]], label:type[1]};
            self.sections.push(section);
        });
        this.do_refresh(true);
    },
    do_refresh: function(new_view) {
        var view = this.view_manager.active_view;
        var the_condition = this.sections.length > 0 && _.detect(this.sections,
            function(x) {return x.elements.length > 0;}) != undefined
            && (!new_view || view != 'list');

        this.$element.toggleClass('open-sidebar', the_condition)
                     .toggleClass('closed-sidebar', !the_condition);

        this.$element.html(QWeb.render("ViewManager.sidebar.internal", { sidebar: this, view: view }));

        var self = this;
        this.$element.find(".toggle-sidebar").click(function(e) {
            self.$element.toggleClass('open-sidebar closed-sidebar');
            e.stopPropagation();
            e.preventDefault();
        });

        this.$element.find("a.oe_sidebar_action_a").click(function(e) {
            var $this = jQuery(this);
            var index = $this.attr("data-index").split('-');
            var action = self.sections[index[0]].elements[index[1]];
            action.flags = {
                new_window : true
            };
            self.session.action_manager.do_action(action);
            e.stopPropagation();
            e.preventDefault();
        });
    },
    start: function() {
        this._super();
        this.do_refresh(false);
    }
});

openerp.base.NullSidebar = openerp.base.generate_null_object_class(openerp.base.Sidebar);

openerp.base.Export = openerp.base.Dialog.extend({
    dialog_title: "Export",
    template: 'ExportDialog',
    identifier_prefix: 'export_dialog',
    init: function (session, model, domain) {
        this._super();
    },
    start: function () {
        this._super();
        this.$element.html(this.render());
    },
    on_button_Export: function() {
        console.log("Export")
    },
    on_button_Cancel: function() {
        this.$element.dialog("close");
    }
});

openerp.base.View = openerp.base.Controller.extend({
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
     * @param {Function} on_no_action callback to execute if the action does not generate any result (no new action)
     */
    execute_action: function (action_data, dataset, action_manager, record_id, on_no_action, on_closed) {
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
                action.flags = {
                    new_window: true
                };
                action_manager.do_action(action, on_closed);
                if (self.view_manager.is_dialog && action.type != 'ir.actions.act_window_close') {
                    handler({
                        result : { type: 'ir.actions.act_window_close' }
                    });
                }
            } else {
                on_no_action(action);
            }
        };

        if (action_data.special) {
            handler({
                result : { type: 'ir.actions.act_window_close', special: action_data.special }
            });
        } else {
            var context = new openerp.base.CompoundContext(dataset.get_context(), action_data.context || {});
            switch(action_data.type) {
                case 'object':
                    return dataset.call_button(action_data.name, [[record_id], context], handler);
                case 'action':
                    return this.rpc('/base/action/load', { action_id: parseInt(action_data.name, 10), context: context }, handler);
                default:
                    return dataset.exec_workflow(record_id, action_data.name, handler);
            }
        }
    },
    /**
     * Directly set a view to use instead of calling fields_view_get. This method must
     * be called before start(). When an embedded view is set, underlying implementations
     * of openerp.base.View must use the provided view instead of any other one.
     * @param embedded_view A view.
     */
    set_embedded_view: function(embedded_view) {
        this.embedded_view = embedded_view;
    }
});

/**
 * Registry for all the main views
 */
openerp.base.views = new openerp.base.Registry();

openerp.base.ProcessView = openerp.base.Controller.extend({
});

openerp.base.HelpView = openerp.base.Controller.extend({
});

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
