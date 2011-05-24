/*---------------------------------------------------------
 * OpenERP base library
 *---------------------------------------------------------*/

openerp.base.views = function(openerp) {

openerp.base.ActionManager = openerp.base.Controller.extend({
// process all kind of actions
    init: function(session, element_id) {
        this._super(session, element_id);
        this.viewmanager = null;
        this.dialog_stack = []
        // Temporary linking view_manager to session.
        // Will use controller_parent to find it when implementation will be done.
        session.action_manager = this;
    },
    /**
     * Process an action
     * Supported actions: act_window
     */
    do_action: function(action) {
        var self = this;
        action.flags = _.extend({
            sidebar : true,
            search_view : true,
            new_window : false,
            views_switcher : true,
            action_buttons : true,
            pager : true
        }, action.flags || {});
        // instantiate the right controllers by understanding the action
        switch (action.type) {
            case 'ir.actions.act_window':
                if (action.target == 'new') {
                    var element_id = _.uniqueId("act_window_dialog");
                    var dialog = $('<div id="' + element_id + '"></div>');
                    dialog.dialog({
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
                dialog.$element.dialog('destroy');
                dialog.stop();
                break;
            default:
                console.log(_.sprintf("Action manager can't handle action of type %s", action.type), action);
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
        this.views_src = views;
        this.views = {};
        this.flags = this.flags || {};
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
            self.views[view[1]] = { view_id: view[0], controller: null };
        });
        if (this.flags.views_switcher === false) {
            this.$element.find('.oe_vm_switch').hide();
        }
        // switch to the first one in sequence
        return this.on_mode_switch(this.views_src[0][1]);
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
        var view_promise;
        this.active_view = view_type;
        var view = this.views[view_type];
        if (!view.controller) {
            // Lazy loading of views
            var controllerclass = openerp.base.views.get_object(view_type);
            var controller = new controllerclass( this, this.session, this.element_id + "_view_" + view_type, this.dataset, view.view_id);
            view_promise = controller.start();
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

        for (var i in this.views) {
            if (this.views[i].controller) {
                if (i === view_type) {
                    $.when(view_promise).then(this.views[i].controller.do_show);
                } else {
                    this.views[i].controller.do_hide();
                }
            }
        }
        return view_promise;
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

openerp.base.DummyViewManager = openerp.base.generate_dummy(openerp.base.ViewManager, {
    init: function() {
        this.action = {};
    }
});

openerp.base.ViewManagerAction = openerp.base.ViewManager.extend({
    init: function(session, element_id, action) {
        var dataset;
        if(!action.res_id) {
            dataset = new openerp.base.DataSetSearch(session, action.res_model);
        } else {
            dataset = new openerp.base.DataSetStatic(session, action.res_model);
            dataset.ids = [action.res_id];
            dataset.count = 1;
        }
        this._super(session, element_id, dataset, action.views);
        this.action = action;
        this.flags = this.action.flags || {};
        if (action.res_model == 'board.board' && action.views.length == 1 && action.views) {
            // Not elegant but allows to avoid flickering of SearchView#do_hide
            this.flags.search_view = this.flags.pager = this.flags.action_buttons = false;
        }
        if (this.flags.sidebar) {
            this.sidebar = new openerp.base.Sidebar(null, this);
        }
    },
    start: function() {
        var inital_view_loaded = this._super();

        // init sidebar
        if (this.sidebar) {
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

        // init search view
        var searchview_id = this.action.search_view_id && this.action.search_view_id[0];

        var searchview_loaded = this.setup_search_view(
                searchview_id || false, search_defaults);

        // schedule auto_search
        if (searchview_loaded != null && this.action['auto_search']) {
            $.when(searchview_loaded, inital_view_loaded)
                .then(this.searchview.do_search);
        }
    },
    stop: function() {
        // should be replaced by automatic destruction implemented in BaseWidget
        if (this.sidebar) {
            this.sidebar.stop();
        }
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
        this.refresh(true);
    },
    refresh: function(new_view) {
        var view = this.view_manager.active_view;
        the_condition = this.sections.length > 0 && _.detect(this.sections,
            function(x) {return x.elements.length > 0;}) != undefined
            && (!new_view || view != 'list');
        if (!the_condition) {
            this.$element.addClass('closed-sidebar');
            this.$element.removeClass('open-sidebar');
        } else {
            this.$element.addClass('open-sidebar');
            this.$element.removeClass('closed-sidebar');
        }
        
        this.$element.html(QWeb.render("ViewManager.sidebar.internal",this));
        
        var self = this;
        this.$element.find(".toggle-sidebar").click(function(e) {
            self.$element.toggleClass('open-sidebar closed-sidebar');
            e.stopPropagation();
            e.preventDefault();
        });
        
        this.$element.find("a.oe_sidebar_action_a").click(function(e) {
            var $this = jQuery(this);
            var i = $this.attr("data-i");
            var j = $this.attr("data-j");
            var action = self.sections[i].elements[j];
            action.flags = {
                new_window : true
            }
            self.session.action_manager.do_action(action);
            e.stopPropagation();
            e.preventDefault();
        });
    },
    start: function() {
        this._super();
        this.refresh(false);
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
     * @param {Number} [record_id] the identifier of the object on which the action is to be applied
     * @param {Function} on_no_action callback to execute if the action does not generate any result (no new action)
     */
    execute_action: function (action_data, dataset, action_manager, record_id, on_no_action) {
        var handler = function (r) {
            if (r.result && r.result.constructor == Object) {
                action_manager.do_action(r.result);
            } else {
                on_no_action(r.result);
            }
        };

        if (action_data.special) {
            handler({
                result : { type: 'ir.actions.act_window_close' }
            });
        } else {
            var context = _.extend({}, dataset.context, action_data.context || {});
            switch(action_data.type) {
                case 'object':
                    return dataset.call(action_data.name, [record_id], [context], handler);
                case 'action':
                    return this.rpc('/base/action/load', { action_id: parseInt(action_data.name, 10) }, handler);
                default:
                    return dataset.exec_workflow(record_id, action_data.name, handler);
            }
        }
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

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
