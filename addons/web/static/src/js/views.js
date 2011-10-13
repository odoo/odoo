/*---------------------------------------------------------
 * OpenERP web library
 *---------------------------------------------------------*/

openerp.web.views = function(db) {

var _t = db.web._t;

/**
 * Registry for all the client actions key: tag value: widget
 */
db.web.client_actions = new db.web.Registry();

/**
 * Registry for all the main views
 */
db.web.views = new db.web.Registry();

db.web.ActionManager = db.web.Widget.extend({
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
    content_stop: function () {
        if (this.inner_viewmanager) {
            this.inner_viewmanager.stop();
            this.inner_viewmanager = null;
        }
        if (this.client_widget) {
            this.client_widget.stop();
            this.client_widget = null;
        }
    },
    url_update: function(action) {
        var url = {};
        if(action.id)
            url.action_id = action.id;
        // this.url = {
        //     "model": action.res_model,
        //     "domain": action.domain,
        // };
        // action.res_model
        // action.domain
        // action.context
        // after
        // action.views
        // action.res_id
        // mode
        // menu
        this.do_url_set_hash(url);
    },
    do_url_set_hash: function(url) {
    },
    on_url_hashchange: function(url) {
        var self = this;
        if(url && url.action_id) {
            self.rpc("/web/action/load", { action_id: url.action_id }, function(result) {
                    self.do_action(result.result);
                });
        }
    },
    do_action: function(action, on_close) {
        var type = action.type.replace(/\./g,'_');
        var popup = action.target === 'new';
        action.flags = _.extend({
            views_switcher : !popup,
            search_view : !popup,
            action_buttons : !popup,
            sidebar : !popup,
            pager : !popup
        }, action.flags || {});
        if (!(type in this)) {
            console.log("Action manager can't handle action of type " + action.type, action);
            return;
        }
        return this[type](action, on_close);
    },
    ir_actions_act_window: function (action, on_close) {
        if (action.target === 'new') {
            if (this.dialog == null) {
                this.dialog = new db.web.Dialog(this, { title: action.name, width: '80%' });
                if(on_close)
                    this.dialog.on_close.add(on_close);
                this.dialog.start();
            } else {
                this.dialog_viewmanager.stop();
            }
            this.dialog_viewmanager = new db.web.ViewManagerAction(this, action);
            this.dialog_viewmanager.appendTo(this.dialog.$element);
            this.dialog.open();
        } else  {
            this.dialog_stop();
            this.content_stop();
            this.inner_viewmanager = new db.web.ViewManagerAction(this, action);
            this.inner_viewmanager.appendTo(this.$element);
            this.url_update(action);
        }
        /* new window code
            this.rpc("/web/session/save_session_action", { the_action : action}, function(key) {
                var url = window.location.protocol + "//" + window.location.host + window.location.pathname + "?" + jQuery.param({ s_action : "" + key });
                window.open(url,'_blank');
            });
        */
    },
    ir_actions_act_window_close: function (action, on_closed) {
        if (!this.dialog && on_closed) {
            on_closed();
        }
        if (this.dialog && action.context) {
            var model = action.context.active_model;
            if (model === 'base.module.upgrade' || model === 'base.setup.installer') {
                db.webclient.menu.do_reload();
            }
        }
        this.dialog_stop();
    },
    ir_actions_server: function (action, on_closed) {
        var self = this;
        this.rpc('/web/action/run', {
            action_id: action.id,
            context: action.context || {}
        }).then(function (action) {
            self.do_action(action, on_closed)
        });
    },
    ir_actions_client: function (action) {
        this.content_stop();
        var ClientWidget = db.web.client_actions.get_object(action.tag);
        (this.client_widget = new ClientWidget(this, action.params)).appendTo(this);
    },
    ir_actions_report_xml: function(action) {
        var self = this;
        $.blockUI();
        self.rpc("/web/session/eval_domain_and_context", {
            contexts: [action.context],
            domains: []
        }).then(function(res) {
            action = _.clone(action);
            action.context = res.context;
            self.session.get_file({
                url: '/web/report',
                data: {action: JSON.stringify(action)},
                complete: $.unblockUI
            });
        });
    }
});

db.web.ViewManager =  db.web.Widget.extend(/** @lends db.web.ViewManager# */{
    identifier_prefix: "viewmanager",
    template: "ViewManager",
    /**
     * @constructs db.web.ViewManager
     * @extends db.web.Widget
     *
     * @param parent
     * @param dataset
     * @param views
     */
    init: function(parent, dataset, views) {
        this._super(parent);
        this.model = dataset ? dataset.model : undefined;
        this.dataset = dataset;
        this.searchview = null;
        this.last_search = false;
        this.active_view = null;
        this.views_src = _.map(views, function(x) {return x instanceof Array? {view_id: x[0], view_type: x[1]} : x;});
        this.views = {};
        this.flags = this.flags || {};
        this.registry = db.web.views;
    },
    render: function() {
        return db.web.qweb.render(this.template, {
            self: this,
            prefix: this.element_id,
            views: this.views_src});
    },
    /**
     * @returns {jQuery.Deferred} initial view loading promise
     */
    start: function() {
        this._super();
        var self = this;
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
            var controller = new controllerclass(this, this.dataset, view.view_id, view.options);
            if (view.embedded_view) {
                controller.set_embedded_view(view.embedded_view);
            }
            controller.do_switch_view.add_last(this.on_mode_switch);
            var container = $("#" + this.element_id + '_view_' + view_type);
            view_promise = controller.appendTo(container);
            this.views[view_type].controller = controller;
            $.when(view_promise).then(function() {
                self.on_controller_inited(view_type, controller);
                if (self.searchview && view.controller.searchable !== false) {
                    self.do_searchview_search();
                }
            });
        } else if (this.searchview && view.controller.searchable !== false) {
            self.do_searchview_search();
        }

        if (this.searchview) {
            this.searchview[(view.controller.searchable === false || this.searchview.hidden) ? 'hide' : 'show']();
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
     * Sets up the current viewmanager's search view.
     *
     * @param {Number|false} view_id the view to use or false for a default one
     * @returns {jQuery.Deferred} search view startup deferred
     */
    setup_search_view: function(view_id, search_defaults) {
        var self = this;
        if (this.searchview) {
            this.searchview.stop();
        }
        this.searchview = new db.web.SearchView(
                this, this.dataset,
                view_id, search_defaults, this.flags.search_view === false);

        this.searchview.on_search.add(this.do_searchview_search);
        return this.searchview.appendTo($("#" + this.element_id + "_search"));
    },
    do_searchview_search: function(domains, contexts, groupbys) {
        var self = this,
            controller = this.views[this.active_view].controller;
        if (domains || contexts) {
            this.rpc('/web/session/eval_domain_and_context', {
                domains: [this.action.domain || []].concat(domains || []),
                contexts: [this.action.context || {}].concat(contexts || []),
                group_by_seq: groupbys || []
            }, function (results) {
                self.dataset.context = results.context;
                self.dataset.domain = results.domain;
                self.last_search = [results.domain, results.context, results.group_by];
                controller.do_search(results.domain, results.context, results.group_by);
            });
        } else if (this.last_search) {
            controller.do_search.apply(controller, this.last_search);
        }
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
     * Called by children view after executing an action
     */
    on_action_executed: function () {}
});

db.web.ViewManagerAction = db.web.ViewManager.extend(/** @lends oepnerp.web.ViewManagerAction# */{
    template:"ViewManagerAction",
    /**
     * @constructs db.web.ViewManagerAction
     * @extends db.web.ViewManager
     *
     * @param {db.web.ActionManager} parent parent object/widget
     * @param {Object} action descriptor for the action this viewmanager needs to manage its views.
     */
    init: function(parent, action) {
        // dataset initialization will take the session from ``this``, so if we
        // do not have it yet (and we don't, because we've not called our own
        // ``_super()``) rpc requests will blow up.
        this._super(parent, null, action.views);
        this.session = parent.session;
        this.action = action;
        var dataset = new db.web.DataSetSearch(this, action.res_model, action.context, action.domain);
        if (action.res_id) {
            dataset.ids.push(action.res_id);
            dataset.index = 0;
        }
        this.dataset = dataset;
        this.flags = this.action.flags || {};
        if (action.res_model == 'board.board' && action.views.length == 1 && action.views) {
            // Not elegant but allows to avoid form chrome (pager, save/new
            // buttons, sidebar, ...) displaying
            this.flags.search_view = this.flags.pager = this.flags.sidebar = this.flags.action_buttons = false;
        }

        // setup storage for session-wise menu hiding
        if (this.session.hidden_menutips) {
            return;
        }
        this.session.hidden_menutips = {}
    },
    /**
     * Initializes the ViewManagerAction: sets up the searchview (if the
     * searchview is enabled in the manager's action flags), calls into the
     * parent to initialize the primary view and (if the VMA has a searchview)
     * launches an initial search after both views are done rendering.
     */
    start: function() {
        var self = this,
            searchview_loaded,
            search_defaults = {};
        _.each(this.action.context, function (value, key) {
            var match = /^search_default_(.*)$/.exec(key);
            if (match) {
                search_defaults[match[1]] = value;
            }
        });
        // init search view
        var searchview_id = this.action['search_view_id'] && this.action['search_view_id'][0];

        searchview_loaded = this.setup_search_view(searchview_id || false, search_defaults);

        var main_view_loaded = this._super();

        var manager_ready = $.when(searchview_loaded, main_view_loaded);
        if (searchview_loaded && this.action['auto_search'] !== false) {
            // schedule auto_search
            manager_ready.then(this.searchview.do_search);
        }

        this.$element.find('.oe_get_xml_view').click(function () {
            // TODO: add search view?
            $('<pre>').text(db.web.json_node_to_xml(
                self.views[self.active_view].controller.fields_view.arch, true))
                    .dialog({ width: '95%'});
        });
        if (this.action.help && !this.flags.low_profile) {
            var Users = new db.web.DataSet(self, 'res.users'),
                header = this.$element.find('.oe-view-manager-header');
            header.delegate('blockquote button', 'click', function() {
                var $this = $(this);
                //noinspection FallthroughInSwitchStatementJS
                switch ($this.attr('name')) {
                case 'disable':
                    Users.write(self.session.uid, {menu_tips:false});
                case 'hide':
                    $this.closest('blockquote').hide();
                    self.session.hidden_menutips[self.action.id] = true;
                }
            });
            if (!(self.action.id in self.session.hidden_menutips)) {
                Users.read_ids([this.session.uid], ['menu_tips'], function(users) {
                    var user = users[0];
                    if (!(user && user.id === self.session.uid)) {
                        return;
                    }
                    header.find('blockquote').toggle(user.menu_tips);
                });
            }
        }

        return manager_ready;
    },
    on_mode_switch: function (view_type) {
        var self = this;
        return $.when(
            this._super(view_type),
            this.shortcut_check(this.views[view_type])).then(function () {
                var view_id = self.views[self.active_view].controller.fields_view.view_id;
                self.$element.find('.oe_get_xml_view span').text(view_id);
        });
    },
    shortcut_check : function(view) {
        var self = this;
        var grandparent = this.widget_parent && this.widget_parent.widget_parent;
        // display shortcuts if on the first view for the action
        var $shortcut_toggle = this.$element.find('.oe-shortcut-toggle');
        if (!(grandparent instanceof db.web.WebClient) ||
            !(view.view_type === this.views_src[0].view_type
                && view.view_id === this.views_src[0].view_id)) {
            $shortcut_toggle.hide();
            return;
        }
        $shortcut_toggle.removeClass('oe-shortcut-remove').show();
        if (_(this.session.shortcuts).detect(function (shortcut) {
                    return shortcut.res_id === self.session.active_id; })) {
            $shortcut_toggle.addClass("oe-shortcut-remove");
        }
        this.shortcut_add_remove();
    },
    shortcut_add_remove: function() {
        var self = this;
        var $shortcut_toggle = this.$element.find('.oe-shortcut-toggle');
        $shortcut_toggle
            .unbind("click")
            .click(function() {
                if ($shortcut_toggle.hasClass("oe-shortcut-remove")) {
                    $(self.session.shortcuts.binding).trigger('remove-current');
                    $shortcut_toggle.removeClass("oe-shortcut-remove");
                } else {
                    $(self.session.shortcuts.binding).trigger('add', {
                        'user_id': self.session.uid,
                        'res_id': self.session.active_id,
                        'resource': 'ir.ui.menu',
                        'name': self.action.name
                    });
                    $shortcut_toggle.addClass("oe-shortcut-remove");
                }
            });
    },
    /**
     * Intercept do_action resolution from children views
     */
    on_action_executed: function () {
        return new db.web.DataSet(this, 'res.log')
                .call('get', [], this.do_display_log);
    },
    /**
     * @param {Array<Object>} log_records
     */
    do_display_log: function (log_records) {
        var self = this,
            $logs = this.$element.find('ul.oe-view-manager-logs:first').empty();
        _(log_records).each(function (record) {
            $(_.sprintf('<li><a href="#">%s</a></li>', record.name))
                .appendTo($logs)
                .delegate('a', 'click', function (e) {
                    self.do_action({
                        type: 'ir.actions.act_window',
                        res_model: record.res_model,
                        res_id: record.res_id,
                        // TODO: need to have an evaluated context here somehow
                        //context: record.context,
                        views: [[false, 'form']]
                    });
                    return false;
                });
        });
    }
});

db.web.Sidebar = db.web.Widget.extend({
    init: function(parent, element_id) {
        this._super(parent, element_id);
        this.items = {};
        this.sections = {};
    },
    start: function() {
        this._super(this);
        var self = this;
        this.$element.html(db.web.qweb.render('Sidebar'));
        this.$element.find(".toggle-sidebar").click(function(e) {
            self.do_toggle();
        });
    },

    call_default_on_sidebar: function(item) {
        var func_name = 'on_sidebar_' + _.underscored(item.label);
        var fn = this.widget_parent[func_name];
        if(typeof fn === 'function') {
            fn(item);
        }
    },

    add_default_sections: function() {
        this.add_section(_t('Customize'), 'customize');
        this.add_items('customize', [
            {
                label: _t("Manage Views"),
                callback: this.call_default_on_sidebar,
                title: _t("Manage views of the current object"),
            }, {
                label: _t("Edit Workflow"),
                callback: this.call_default_on_sidebar,
                title: _t("Manage views of the current object"),
                classname: 'oe_hide oe_sidebar_edit_workflow'
            }, {
                label: _t("Customize Object"),
                callback: this.call_default_on_sidebar,
                title: _t("Manage views of the current object"),
            }
        ]);

        this.add_section(_t('Other Options'), 'other');
        this.add_items('other', [ 
            {
                label: _t("Import"),
                callback: this.call_default_on_sidebar,
            }, {
                label: _t("Export"),
                callback: this.call_default_on_sidebar,
            }, {
                label: _t("Translate"),
                callback: this.call_default_on_sidebar,
                classname: 'oe_sidebar_translate oe_hide'
            }, {
                label: _t("View Log"),
                callback: this.call_default_on_sidebar,
                classname: 'oe_hide oe_sidebar_view_log'
            }
        ]);
    },

    add_toolbar: function(toolbar) {
        var self = this;
        _.each([['print', _t("Reports")], ['action', _t("Actions")], ['relate', _t("Links")]], function(type) {
            var items = toolbar[type[0]];
            if (items.length) {
                for (var i = 0; i < items.length; i++) {
                    items[i] = {
                        label: items[i]['name'],
                        action: items[i],
                        classname: 'oe_sidebar_' + type[0]
                    }
                }
                self.add_section(type[1], type[0]);
                self.add_items(type[0], items);
            }
        });
    },
    
    add_section: function(name, code) {
        if(!code) code = _.underscored(name);
        var $section = this.sections[code];

        if(!$section) {
            section_id = _.uniqueId(this.element_id + '_section_' + code + '_');
            var $section = $(db.web.qweb.render("Sidebar.section", {
                section_id: section_id,
                name: name,
                classname: 'oe_sidebar_' + code,
            }));
            $section.appendTo(this.$element.find('div.sidebar-actions'));
            this.sections[code] = $section;
        }
        return $section;
    },

    add_items: function(section_code, items) {
        // An item is a dictonary : {
        //    label: label to be displayed for the link,
        //    action: action to be launch when the link is clicked,
        //    callback: a function to be executed when the link is clicked,
        //    classname: optional dom class name for the line,
        //    title: optional title for the link
        // }
        // Note: The item should have one action or/and a callback
        //

        var self = this,
            $section = this.add_section(_.titleize(section_code.replace('_', ' ')), section_code),
            section_id = $section.attr('id');

        if (items) {
            for (var i = 0; i < items.length; i++) {
                items[i].element_id = _.uniqueId(section_id + '_item_');
                this.items[items[i].element_id] = items[i];
            }

            var $items = $(db.web.qweb.render("Sidebar.section.items", {items: items}));

            $items.find('a.oe_sidebar_action_a').click(function() {
                var item = self.items[$(this).attr('id')];
                if (item.callback) {
                    item.callback.apply(self, [item]);
                }
                if (item.action) {
                    var ids = self.widget_parent.get_selected_ids();
                    if (ids.length == 0) {
                        //TODO: make prettier warning?
                        $("<div />").text(_t("You must choose at least one record.")).dialog({
                            title: _t("Warning"),
                            modal: true
                        });
                        return false;
                    }
                    var additional_context = {
                        active_id: ids[0],
                        active_ids: ids,
                        active_model: self.widget_parent.dataset.model
                    };
                    self.rpc("/web/action/load", {
                        action_id: item.action.id,
                        context: additional_context
                    }, function(result) {
                        result.result.context = _.extend(result.result.context || {},
                            additional_context);
                        result.result.flags = result.result.flags || {};
                        result.result.flags.new_window = true;
                        self.do_action(result.result);
                    });
                }
                return false;
            });
        
            var $ul = $section.find('ul');
            if(!$ul.length) {
                $ul = $('<ul/>').appendTo($section);
            }
            $items.appendTo($ul);
        }
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

db.web.TranslateDialog = db.web.Dialog.extend({
    dialog_title: _t("Translations"),
    init: function(view) {
        // TODO fme: should add the language to fields_view_get because between the fields view get
        // and the moment the user opens the translation dialog, the user language could have been changed
        this.view_language = view.session.user_context.lang;
        this['on_button' + _t("Save")] = this.on_button_Save;
        this['on_button' + _t("Close")] = this.on_button_Close;
        this._super(view, {
            width: '80%',
            height: '80%'
        });
        this.view = view;
        this.view_type = view.fields_view.type || '';
        this.$fields_form = null;
        this.$view_form = null;
        this.$sidebar_form = null;
        this.translatable_fields_keys = _.map(this.view.translatable_fields || [], function(i) { return i.name });
        this.languages = null;
        this.languages_loaded = $.Deferred();
        (new db.web.DataSetSearch(this, 'res.lang', this.view.dataset.get_context(),
            [['translatable', '=', '1']])).read_slice(['code', 'name'], { sort: 'id' }, this.on_languages_loaded);
    },
    start: function() {
        var self = this;
        this._super();
        $.when(this.languages_loaded).then(function() {
            self.$element.html(db.web.qweb.render('TranslateDialog', { widget: self }));
            self.$element.tabs();
            if (!(self.view.translatable_fields && self.view.translatable_fields.length)) {
                self.hide_tabs('fields');
                self.select_tab('view');
            }
            self.$fields_form = self.$element.find('.oe_translation_form');
            self.$fields_form.find('.oe_trad_field').change(function() {
                $(this).toggleClass('touched', ($(this).val() != $(this).attr('data-value')));
            });
        });
        return this;
    },
    on_languages_loaded: function(langs) {
        this.languages = langs;
        this.languages_loaded.resolve();
    },
    do_load_fields_values: function(callback) {
        var self = this,
            deffered = [];
        this.$fields_form.find('.oe_trad_field').val('').removeClass('touched');
        _.each(self.languages, function(lg) {
            var deff = $.Deferred();
            deffered.push(deff);
            var callback = function(values) {
                _.each(self.translatable_fields_keys, function(f) {
                    self.$fields_form.find('.oe_trad_field[name="' + lg.code + '-' + f + '"]').val(values[0][f] || '').attr('data-value', values[0][f] || '');
                });
                deff.resolve();
            };
            if (lg.code === self.view_language) {
                var values = {};
                _.each(self.translatable_fields_keys, function(field) {
                    values[field] = self.view.fields[field].get_value();
                });
                callback([values]);
            } else {
                self.rpc('/web/dataset/get', {
                    model: self.view.dataset.model,
                    ids: [self.view.datarecord.id],
                    fields: self.translatable_fields_keys,
                    context: self.view.dataset.get_context({
                        'lang': lg.code
                    })}, callback);
            }
        });
        $.when.apply(null, deffered).then(callback);
    },
    show_tabs: function() {
        for (var i = 0; i < arguments.length; i++) {
            this.$element.find('ul.oe_translate_tabs li a[href$="' + arguments[i] + '"]').parent().show();
        }
    },
    hide_tabs: function() {
        for (var i = 0; i < arguments.length; i++) {
            this.$element.find('ul.oe_translate_tabs li a[href$="' + arguments[i] + '"]').parent().hide();
        }
    },
    select_tab: function(name) {
        this.show_tabs(name);
        var index = this.$element.find('ul.oe_translate_tabs li a[href$="' + arguments[i] + '"]').parent().index() - 1;
        this.$element.tabs('select', index);
    },
    open: function(field) {
        var self = this,
            sup = this._super;
        $.when(this.languages_loaded).then(function() {
            if (self.view.translatable_fields && self.view.translatable_fields.length) {
                self.do_load_fields_values(function() {
                    sup.call(self);
                    if (field) {
                        // TODO: focus and scroll to field
                    }
                });
            } else {
                sup.call(self);
            }
        });
    },
    on_button_Save: function() {
        var trads = {},
            self = this;
        self.$fields_form.find('.oe_trad_field.touched').each(function() {
            var field = $(this).attr('name').split('-');
            if (!trads[field[0]]) {
                trads[field[0]] = {};
            }
            trads[field[0]][field[1]] = $(this).val();
        });
        _.each(trads, function(data, code) {
            if (code === self.view_language) {
                _.each(data, function(value, field) {
                    self.view.fields[field].set_value(value);
                });
            } else {
                self.view.dataset.write(self.view.datarecord.id, data, { 'lang': code });
            }
        });
        this.close();
    },
    on_button_Close: function() {
        this.close();
    }
});

db.web.View = db.web.Widget.extend(/** @lends db.web.View# */{
    template: "EmptyComponent",
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
    open_translate_dialog: function(field) {
        if (!this.translate_dialog) {
            this.translate_dialog = new db.web.TranslateDialog(this).start();
        }
        this.translate_dialog.open(field);
    },
    /**
     * Fetches and executes the action identified by ``action_data``.
     *
     * @param {Object} action_data the action descriptor data
     * @param {String} action_data.name the action name, used to uniquely identify the action to find and execute it
     * @param {String} [action_data.special=null] special action handlers (currently: only ``'cancel'``)
     * @param {String} [action_data.type='workflow'] the action type, if present, one of ``'object'``, ``'action'`` or ``'workflow'``
     * @param {Object} [action_data.context=null] additional action context, to add to the current context
     * @param {db.web.DataSet} dataset a dataset object used to communicate with the server
     * @param {Object} [record_id] the identifier of the object on which the action is to be applied
     * @param {Function} on_closed callback to execute when dialog is closed or when the action does not generate any result (no new action)
     */
    do_execute_action: function (action_data, dataset, record_id, on_closed) {
        var self = this;
        var result_handler = function () {
            if (on_closed) { on_closed.apply(null, arguments); }
            if (self.widget_parent && self.widget_parent.on_action_executed) {
                return self.widget_parent.on_action_executed.apply(null, arguments);
            }
        };
        var handler = function (r) {
            var action = r.result;
            if (action && action.constructor == Object) {
                return self.rpc('/web/session/eval_domain_and_context', {
                    contexts: [dataset.get_context(), action.context || {}, {
                        active_id: record_id || false,
                        active_ids: [record_id || false],
                        active_model: dataset.model
                    }],
                    domains: []
                }).pipe(function (results) {
                    action.context = results.context
                    return self.do_action(action, result_handler);
                });
            } else {
                return result_handler();
            }
        };

        var context = new db.web.CompoundContext(dataset.get_context(), action_data.context || {});

        if (action_data.special) {
            return handler({result: {"type":"ir.actions.act_window_close"}});
        } else if (action_data.type=="object") {
            return dataset.call_button(action_data.name, [[record_id], context], handler);
        } else if (action_data.type=="action") {
            return this.rpc('/web/action/load', { action_id: parseInt(action_data.name, 10), context: context }, handler);
        } else  {
            return dataset.exec_workflow(record_id, action_data.name, handler);
        }
    },
    /**
     * Directly set a view to use instead of calling fields_view_get. This method must
     * be called before start(). When an embedded view is set, underlying implementations
     * of db.web.View must use the provided view instead of any other one.
     *
     * @param embedded_view A view.
     */
    set_embedded_view: function(embedded_view) {
        this.embedded_view = embedded_view;
        this.options.sidebar = false;
    },
    do_switch_view: function(view) {
    },
    do_search: function(view) {
    },

    set_common_sidebar_sections: function(sidebar) {
        sidebar.add_default_sections();
    },
    on_sidebar_manage_views: function() {
        if (this.fields_view && this.fields_view.arch) {
            $('<xmp>' + db.web.json_node_to_xml(this.fields_view.arch, true) + '</xmp>').dialog({ width: '95%', height: 600});
        } else {
            this.notification.warn("Manage Views", "Could not find current view declaration");
        }
    },
    on_sidebar_edit_workflow: function() {
        console.log('Todo');
    },
    on_sidebar_customize_object: function() {
        console.log('Todo');
    },
    on_sidebar_import: function() {
        var import_view = new db.web.DataImport(this, this.dataset);
        import_view.start();
    },
    on_sidebar_export: function() {
        var export_view = new db.web.DataExport(this, this.dataset);
        export_view.start();
    },
    on_sidebar_translate: function() {
        this.open_translate_dialog();
    },
    on_sidebar_view_log: function() {
    }
});

db.web.json_node_to_xml = function(node, single_quote, indent) {
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
    if (node.children && node.children.length) {
        r += '>\n';
        var childs = [];
        for (var i = 0, ii = node.children.length; i < ii; i++) {
            childs.push(db.web.json_node_to_xml(node.children[i], single_quote, indent + 1));
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
