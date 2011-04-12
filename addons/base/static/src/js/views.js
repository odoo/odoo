/*---------------------------------------------------------
 * OpenERP base library
 *---------------------------------------------------------*/

openerp.base.views = function(openerp) {

openerp.base.ActionManager = openerp.base.Controller.extend({
// process all kind of actions
    init: function(session, element_id) {
        this._super(session, element_id);
        this.viewmanager = null;
        // Temporary linking view_manager to session.
        // Will use controller_parent to find it when implementation will be done.
        session.view_manager = this;
    },
    /**
     * Process an action
     * Supported actions: act_window
     */
    do_action: function(action) {
        // instantiate the right controllers by understanding the action
        if(action.type == "ir.actions.act_window") {
            if (this.viewmanager) {
                this.viewmanager.stop();
            }
            this.viewmanager = new openerp.base.ViewManagerAction(this.session,this.element_id, action, true);
            this.viewmanager.start();
        }
    }
});

/**
 * Registry for all the main views
 */
openerp.base.views = new openerp.base.Registry();

openerp.base.ViewManager =  openerp.base.Controller.extend({
    init: function(session, element_id, dataset, views) {
        this._super(session, element_id);
        this.model = dataset.model;
        this.dataset = dataset;
        this.searchview = null;
        this.active_view = null;
        this.views_src = views;
        this.views = {};
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

        if(this.searchview) {
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
        this.searchview.on_search.add(function() {
            self.views[self.active_view].controller.do_search.apply(self, arguments);
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
    init: function(session, element_id, action, sidebar) {
        var dataset = new openerp.base.DataSetSearch(session, action.res_model);
        this._super(session, element_id, dataset, action.views);
        this.action = action;
        this.sidebar = sidebar;
        if (sidebar)
            this.sidebar = new openerp.base.Sidebar(null, this);
    },
    start: function() {
        var inital_view_loaded = this._super();

        // init sidebar
        if (this.sidebar) {
            this.$element.find('.view-manager-main-sidebar').html(this.sidebar.render());
            this.sidebar.start();
        }

        // init search view
        var view_id = this.action.search_view_id ? this.action.search_view_id[0] || false : false;
        var search_defaults = {};
        _.each(this.action.context, function (value, key) {
            var match = /^search_default_(.*)$/.exec(key);
            if (match) {
                search_defaults[match[1]] = value;
            }
        });
        var searchview_loaded = null;
        if (view_id) {
            searchview_loaded = this.setup_search_view(view_id,search_defaults);
        }

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
        this.refresh();
    },
    refresh: function() {
        this.$element.html(QWeb.render("ViewManager.sidebar.internal", _.extend({_:_}, this)));
        var self = this;
        this.$element.find(".toggle-sidebar").click(function(e) {
            self.$element.toggleClass('open-sidebar closed-sidebar');
            e.stopPropagation();
            e.preventDefault();
        });
        this.$element.find("a").click(function(e) {
            var $this = jQuery(this);
            var i = $this.attr("data-i");
            var j = $this.attr("data-j");
            var action = self.sections[i].elements[j];
            (new openerp.base.ExternalActionManager(self.view_manager.session, null)) .handle_action(action);
            e.stopPropagation();
            e.preventDefault();
        });
    },
    start: function() {
        this._super();
        this.refresh();
    }
});

openerp.base.ExternalActionManager = openerp.base.Controller.extend({
    handle_action: function(action) {
        if(action.type=="ir.actions.act_window") {
            if(action.target=="new") {
                var element_id = _.uniqueId("act_window_dialog");
                var dialog = $('<div id="'+element_id+'"></div>');
                dialog.dialog({
                    title: action.name
                });
                var viewmanager = new openerp.base.ViewManagerAction(this.session ,element_id, action, false);
                viewmanager.start();
            } else if (action.target == "current") {
                this.rpc("/base/session/save_session_action", {the_action:action}, function(key) {
                    var url = window.location.protocol + "//" + window.location.host +
                            window.location.pathname + "?" + jQuery.param({s_action:""+key});
                    window.open(url);
                });
            }
        }
        // TODO: show an error like "not implemented" here
        // since we don't currently have any way to handle errors do you have any better idea
        // than using todos?
    }
});

openerp.base.views.add('calendar', 'openerp.base.CalendarView');
openerp.base.CalendarView = openerp.base.Controller.extend({
    start: function () {
        this._super();
        this.$element.append('Calendar view');
    },
    do_show: function () {
        this.$element.show();
    },
    do_hide: function () {
        this.$element.hide();
    }
});

openerp.base.views.add('gantt', 'openerp.base.GanttView');
openerp.base.GanttView = openerp.base.Controller.extend({
    start: function () {
        this._super();
        this.$element.append('Gantt view');
    },
    do_show: function () {
        this.$element.show();
    },
    do_hide: function () {
        this.$element.hide();
    }
});

openerp.base.views.add('tree', 'openerp.base.TreeView');
openerp.base.TreeView = openerp.base.Controller.extend({
/**
 * Genuine tree view (the one displayed as a tree, not the list)
 */
    start: function () {
        this._super();
        this.$element.append('Tree view');
    },
    do_show: function () {
        this.$element.show();
    },
    do_hide: function () {
        this.$element.hide();
    }
});

openerp.base.views.add('graph', 'openerp.base.GraphView');
openerp.base.GraphView = openerp.base.Controller.extend({
    start: function () {
        this._super();
        this.$element.append('Graph view');
    },
    do_show: function () {
        this.$element.show();
    },
    do_hide: function () {
        this.$element.hide();
    }
});

openerp.base.ProcessView = openerp.base.Controller.extend({
});

openerp.base.HelpView = openerp.base.Controller.extend({
});

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
