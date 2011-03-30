/*---------------------------------------------------------
 * OpenERP base library
 *---------------------------------------------------------*/

openerp.base.views = function(openerp) {

// process all kind of actions
openerp.base.ActionManager = openerp.base.Controller.extend({
    init: function(session, element_id) {
        this._super(session, element_id);
        this.action = null;
        this.viewmanager = null;
    },
    /**
     * Process an action
     * Supported actions: act_window
     */
    do_action: function(action) {
        // instantiate the right controllers by understanding the action
        this.action = action;
        if(action.type == "ir.actions.act_window") {
            this.viewmanager = new openerp.base.ViewManager(this.session,this.element_id);
            this.viewmanager.do_action_window(action);
            this.viewmanager.start();
        }
    }
});

// This will be ViewManager Abstract/Common
openerp.base.ViewManager =  openerp.base.Controller.extend({
    init: function(session, element_id) {
        this._super(session, element_id);
        this.action = null;
        this.dataset = null;
        this.searchview_id = false;
        this.searchview = null;
        this.search_visible = true;
        // this.views = { "list": { "view_id":1234, "controller": instance} }
        this.views = {};
    },
    start: function() {
    },
    on_mode_switch: function(view_type) {
        for (var i in this.views) {
           this.views[i].controller.$element.toggle(i === view_type);
        }
    },
    /**
     * Extract search view defaults from the current action's context.
     *
     * These defaults are of the form {search_default_*: value}
     *
     * @returns {Object} a clean defaults mapping of {field_name: value}
     */
    search_defaults: function () {
        var defaults = {};
        _.each(this.action.context, function (value, key) {
            var match = /^search_default_(.*)$/.exec(key);
            if (match) {
                defaults[match[1]] = value;
            }
        });
        return defaults;
    },
    do_action_window: function(action) {
        var self = this;
        var prefix_id = "#" + this.element_id;
        this.action = action;
        this.dataset = new openerp.base.DataSet(this.session, action.res_model);
        this.dataset.start();

        this.$element.html(QWeb.render("ViewManager", {"prefix": this.element_id, views: action.views}));

        this.searchview_id = false;
        if(this.search_visible && action.search_view_id) {
            this.searchview_id = action.search_view_id[0];
            var searchview = this.searchview = new openerp.base.SearchView(
                    this.session, this.element_id + "_search",
                    this.dataset, this.searchview_id,
                    this.search_defaults());
            searchview.on_search.add(this.do_search);
            searchview.start();

            if (action['auto_search']) {
                searchview.on_loaded.add_last(
                    searchview.do_search);
            }
        }
        for(var i = 0; i < action.views.length; i++)  {
            var view_id, controller;
            view_id = action.views[i][0];
            if(action.views[i][1] == "tree") {
                controller = new openerp.base.ListView(this.session, this.element_id + "_view_tree", this.dataset, view_id);
                controller.start();
                this.views.tree = { view_id: view_id, controller: controller };
                this.$element.find(prefix_id + "_button_tree").bind('click',function(){
                    self.on_mode_switch("tree");
                });
            } else if(action.views[i][1] == "form") {
                controller = new openerp.base.FormView(this.session, this.element_id + "_view_form", this.dataset, view_id);
                controller.start();
                this.views.form = { view_id: view_id, controller: controller };
                this.$element.find(prefix_id + "_button_form").bind('click',function(){
                   self.on_mode_switch("form");
                });
            }
        }
        // switch to the first one in sequence
        this.on_mode_switch("tree");
    },
    // create when root, also add to parent when o2m
    on_create: function() {
    },
    on_remove: function() {
    },
    on_edit: function() {
    },
    do_search: function (domains, contexts, groupbys) {
        var self = this;
        this.rpc('/base/session/eval_domain_and_context', {
            domains: domains,
            contexts: contexts,
            group_by_seq: groupbys
        }, function (results) {
            // TODO: handle non-empty results.group_by with read_group
            self.dataset.set({
                context: results.context,
                domain: results.domain
            }).fetch(0, self.action.limit);
        });
    }
});

// Extends view manager
openerp.base.ViewManagerRoot = openerp.base.Controller.extend({
});

// Extends view manager
openerp.base.ViewManagerUsedAsAMany2One = openerp.base.Controller.extend({
});

/**
 * Base class for widgets. Handle rendering (based on a QWeb template), identifier
 * generation, parenting and destruction of the widget.
 */
openerp.base.BaseWidget = openerp.base.Controller.extend({
    /**
     * The name of the QWeb template that will be used for rendering. Must be redifined
     * in subclasses or the render() method can not be used.
     * 
     * @type string
     */
    template: null,
    /**
     * The prefix used to generate an id automatically. Should be redifined in subclasses.
     * If it is not defined, a default identifier will be used.
     * 
     * @type string
     */
    identifier_prefix: 'generic-identifier',
    /**
     * Contructor. Also initialize the identifier.
     * 
     * @params {openerp.base.search.BaseWidget} parent The parent widget.
     */
    init: function (parent) {
        this.children = [];
        this.parent = null;
        this.set_parent(parent);
        this.make_id(this.identifier_prefix);
    },
    /**
     * Sets and returns a globally unique identifier for the widget.
     *
     * If a prefix is appended, the identifier will be appended to it.
     *
     * @params sections prefix sections, empty/falsy sections will be removed
     */
    make_id: function () {
        this.element_id = _.uniqueId(_.toArray(arguments).join('_'));
        return this.element_id;
    },
    /**
     * "Starts" the widgets. Called at the end of the rendering, this allows
     * to get a jQuery object referring to the DOM ($element attribute).
     */
    start: function () {
        this._super();
        var tmp = document.getElementById(this.element_id)
        this.$element = tmp ? $(tmp) : null;
    },
    /**
     * "Stops" the widgets. Called when the view destroys itself, this
     * lets the widgets clean up after themselves.
     */
    stop: function () {
        var tmp_children = this.children;
        this.children = [];
        _.each(tmp_children, function(x) {
            x.stop();
        });
        if(this.$element != null) {
            this.$element.remove();
        }
        this.set_parent(null);
        this._super();
    },
    /**
     * Set the parent of this component, also unregister the previous parent if there
     * was one.
     * 
     * @param {openerp.base.BaseWidget} parent The new parent.
     */
    set_parent: function(parent) {
        if(this.parent) {
            this.parent.children = _.without(this.parent.children, this);
        }
        this.parent = parent;
        if(this.parent) {
            parent.children.push(this);
        }
    },
    /**
     * Render the widget. This.template must be defined.
     * The content of the current object is passed as context to the template.
     * 
     * @param {object} additional Additional context arguments to pass to the template.
     */
    render: function (additional) {
        return QWeb.render(this.template, _.extend({}, this,
                additional != null ? additional : {}));
    }
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

openerp.base.ProcessView = openerp.base.Controller.extend({
});

openerp.base.HelpView = openerp.base.Controller.extend({
});

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
