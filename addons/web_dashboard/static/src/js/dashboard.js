openerp.web_dashboard = function(instance) {
var QWeb = instance.web.qweb,
    _t = instance.web._t;

if (!instance.web_dashboard) {
    /** @namespace */
    instance.web_dashboard = {};
}

instance.web.form.DashBoard = instance.web.form.Widget.extend({
    init: function(view, node) {
        this._super(view, node);
        this.form_template = 'DashBoard';
        this.actions_attrs = {};
        this.action_managers = [];
    },
    start: function() {
        var self = this;
        this._super.apply(this, arguments);

        this.$element.find('.oe-dashboard-column').sortable({
            connectWith: '.oe-dashboard-column',
            handle: '.oe-dashboard-action-header',
            scroll: false
        }).disableSelection().bind('sortstop', self.do_save_dashboard);

        // Events
        this.$element.find('.oe-dashboard-link-reset').click(this.on_reset);
        this.$element.find('.oe-dashboard-link-change_layout').click(this.on_change_layout);

        this.$element.delegate('.oe-dashboard-column .oe-dashboard-fold', 'click', this.on_fold_action);
        this.$element.delegate('.oe-dashboard-column .ui-icon-closethick', 'click', this.on_close_action);

        // Init actions
        _.each(this.node.children, function(column, column_index) {
            _.each(column.children, function(action, action_index) {
                delete(action.attrs.width);
                delete(action.attrs.height);
                delete(action.attrs.colspan);
                self.rpc('/web/action/load', {
                    action_id: parseInt(action.attrs.name, 10)
                }, function(result) {
                    self.on_load_action(result, column_index + '_' + action_index, action.attrs);
                });
            });
        });
    },
    on_reset: function() {
        this.rpc('/web/view/undo_custom', {
            view_id: this.view.fields_view.view_id,
            reset: true
        }, this.do_reload);
    },
    on_change_layout: function() {
        var self = this;
        var qdict = {
            current_layout : this.$element.find('.oe-dashboard').attr('data-layout')
        };
        var $dialog = instance.web.dialog($('<div>'), {
                            modal: true,
                            title: _t("Edit Layout"),
                            width: 'auto',
                            height: 'auto'
                        }).html(QWeb.render('DashBoard.layouts', qdict));
        $dialog.find('li').click(function() {
            var layout = $(this).attr('data-layout');
            $dialog.dialog('destroy');
            self.do_change_layout(layout);
        });
    },
    do_change_layout: function(new_layout) {
        var $dashboard = this.$element.find('.oe-dashboard');
        var current_layout = $dashboard.attr('data-layout');
        if (current_layout != new_layout) {
            var clayout = current_layout.split('-').length,
                nlayout = new_layout.split('-').length,
                column_diff = clayout - nlayout;
            if (column_diff > 0) {
                var $last_column = $();
                $dashboard.find('.oe-dashboard-column').each(function(k, v) {
                    if (k >= nlayout) {
                        $(v).find('.oe-dashboard-action').appendTo($last_column);
                    } else {
                        $last_column = $(v);
                    }
                });
            }
            $dashboard.toggleClass('oe-dashboard-layout_' + current_layout + ' oe-dashboard-layout_' + new_layout);
            $dashboard.attr('data-layout', new_layout);
            this.do_save_dashboard();
        }
    },
    on_fold_action: function(e) {
        var $e = $(e.currentTarget),
            $action = $e.parents('.oe-dashboard-action:first'),
            id = parseInt($action.attr('data-id'), 10);
        if ($e.is('.ui-icon-minusthick')) {
            $action.data('action_attrs').fold = '1';
        } else {
            delete($action.data('action_attrs').fold);
        }
        $e.toggleClass('ui-icon-minusthick ui-icon-plusthick');
        $action.find('.oe-dashboard-action-content').toggle();
        this.do_save_dashboard();
    },
    on_close_action: function(e) {
        if (confirm(_t("Are you sure you want to remove this item ?"))) {
            $(e.currentTarget).parents('.oe-dashboard-action:first').remove();
            this.do_save_dashboard();
        }
    },
    do_save_dashboard: function() {
        var self = this;
        var board = {
                form_title : this.view.fields_view.arch.attrs.string,
                style : this.$element.find('.oe-dashboard').attr('data-layout'),
                columns : []
            };
        this.$element.find('.oe-dashboard-column').each(function() {
            var actions = [];
            $(this).find('.oe-dashboard-action').each(function() {
                var action_id = $(this).attr('data-id'),
                    new_attrs = _.clone($(this).data('action_attrs'));
                if (new_attrs.domain) {
                    new_attrs.domain = new_attrs.domain_string;
                    delete(new_attrs.domain_string);
                }
                if (new_attrs.context) {
                    new_attrs.context = new_attrs.context_string;
                    delete(new_attrs.context_string);
                }
                actions.push(new_attrs);
            });
            board.columns.push(actions);
        });
        var arch = QWeb.render('DashBoard.xml', board);
        this.rpc('/web/view/add_custom', {
            view_id: this.view.fields_view.view_id,
            arch: arch
        }, function() {
            self.$element.find('.oe-dashboard-link-reset').show();
        });
    },
    on_load_action: function(result, index, action_attrs) {
        var self = this,
            action = result.result,
            view_mode = action_attrs.view_mode;

        if (action_attrs.context && action_attrs.context['dashboard_merge_domains_contexts'] === false) {
            // TODO: replace this 6.1 workaround by attribute on <action/>
            action.context = action_attrs.context || {};
            action.domain = action_attrs.domain || [];
        } else {
            if (action_attrs.context) {
                action.context = _.extend((action.context || {}), action_attrs.context);
            }
            if (action_attrs.domain) {
                action.domain = action.domain || [];
                action.domain.unshift.apply(action.domain, action_attrs.domain);
            }
        }

        var action_orig = _.extend({ flags : {} }, action);

        if (view_mode && view_mode != action.view_mode) {
            var action_view_mode = action.view_mode.split(',');
            action.views = _.map(view_mode.split(','), function(mode) {
                if (_.indexOf(action_view_mode, mode) < 0) {
                    return [false, mode == 'tree' ? 'list': mode];
                } else {
                    mode = mode === 'tree' ? 'list' : mode;
                    return _.find(action.views, function(view) {
                        return view[1] == mode;
                    });
                }
            });
        }

        action.flags = {
            search_view : false,
            sidebar : false,
            views_switcher : false,
            action_buttons : false,
            pager: false,
            low_profile: true,
            display_title: false,
            list: {
                selectable: false
            }
        };
        var am = new instance.web.ActionManager(this),
            // FIXME: ideally the dashboard view shall be refactored like kanban.
            $action = $('#' + this.view.element_id + '_action_' + index);
        $action.parent().data('action_attrs', action_attrs);
        this.action_managers.push(am);
        am.appendTo($action);
        am.do_action(action);
        am.do_action = function (action) {
            self.do_action(action);
        };
        if (action_attrs.creatable && action_attrs.creatable !== 'false') {
            var action_id = parseInt(action_attrs.creatable, 10);
            $action.parent().find('button.oe_dashboard_button_create').click(function() {
                if (isNaN(action_id)) {
                    action_orig.flags.default_view = 'form';
                    self.do_action(action_orig);
                } else {
                    self.rpc('/web/action/load', {
                        action_id: action_id
                    }, function(result) {
                        result.result.flags = result.result.flags || {};
                        result.result.flags.default_view = 'form';
                        self.do_action(result.result);
                    });
                }
            });
        }
        if (am.inner_viewmanager) {
            am.inner_viewmanager.on_mode_switch.add(function(mode) {
                var new_views = [];
                _.each(action_orig.views, function(view) {
                    new_views[view[1] === mode ? 'unshift' : 'push'](view);
                });
                if (!new_views.length || new_views[0][1] !== mode) {
                    new_views.unshift([false, mode]);
                }
                action_orig.views = new_views;
                action_orig.res_id = am.inner_viewmanager.dataset.ids[am.inner_viewmanager.dataset.index];
                self.do_action(action_orig);
            });
        }
    },
    renderElement: function() {
        // We should start with three columns available
        for (var i = this.node.children.length; i < 3; i++) {
            this.node.children.push({
                tag: 'column',
                attrs: {},
                children: []
            });
        }
        var rendered = QWeb.render(this.form_template, this);
        this.$element.html(rendered);
    },
    do_reload: function() {
        var view_manager = this.view.getParent(),
            action_manager = view_manager.getParent();
        this.view.destroy();
        action_manager.do_action(view_manager.action);
    }
});
instance.web.form.DashBoardLegacy = instance.web.form.DashBoard.extend({
    renderElement: function() {
        if (this.node.tag == 'hpaned') {
            this.node.attrs.style = '2-1';
        } else if (this.node.tag == 'vpaned') {
            this.node.attrs.style = '1';
        }
        this.node.tag = 'board';
        _.each(this.node.children, function(child) {
            if (child.tag.indexOf('child') == 0) {
                child.tag = 'column';
                var actions = [], first_child = child.children[0];
                if (first_child && first_child.tag == 'vpaned') {
                    _.each(first_child.children, function(subchild) {
                        actions.push.apply(actions, subchild.children);
                    });
                    child.children = actions;
                }
            }
        });
        this._super(this);
    }
});

instance.web.form.tags.add('hpaned', 'instance.web.form.DashBoardLegacy');
instance.web.form.tags.add('vpaned', 'instance.web.form.DashBoardLegacy');
instance.web.form.tags.add('board', 'instance.web.form.DashBoard');

/*
 * ConfigOverview
 * This client action designed to be used as a dashboard widget display
 * ir.actions.todo in a fancy way
 */
instance.web.client_actions.add( 'board.config.overview', 'instance.web_dashboard.ConfigOverview');
instance.web_dashboard.ConfigOverview = instance.web.View.extend({
    template: 'ConfigOverview',
    init: function (parent) {
        this._super(parent);
        this.user = _.extend(new instance.web.DataSet(this, 'res.users'), {
            index: 0,
            ids: [this.session.uid]
        });
        this.dataset = new instance.web.DataSetSearch(this, 'ir.actions.todo');
    },
    start: function () {
        var self = this;
        return this.user.read_index(['groups_id']).pipe(function(record) {
            var todos_filter = [
                ['type', '!=', 'automatic'],
                '|', ['groups_id', '=', false],
                     ['groups_id', 'in', record['groups_id']]];
            return $.when(
                self.dataset.read_slice(
                    ['state', 'action_id', 'category_id'],
                    { domain: todos_filter }
                ),
                self.dataset.call('progress').pipe(
                        function (arg) { return arg; }, null))
        }, null).then(this.on_records_loaded);

    },
    on_records_loaded: function (records, progress) {
        var grouped_todos = _(records).chain()
            .map(function (record) {
                return {
                    id: record.id,
                    name: record.action_id[1],
                    done: record.state !== 'open',
                    to_do: record.state === 'open',
                    category: record['category_id'][1] || _t("Uncategorized")
                }
            })
            .groupBy(function (record) {return record.category})
            .value();
        this.$element.html(QWeb.render('ConfigOverview.content', {
            completion: 100 * progress.done / progress.total,
            groups: grouped_todos,
            task_title: _t("Execute task \"%s\""),
            checkbox_title: _t("Mark this task as done"),
            _: _
        }));
        var $progress = this.$element.find('div.oe-config-progress-bar');
        $progress.progressbar({value: $progress.data('completion')});

        var self = this;
        this.$element.find('dl')
            .delegate('input', 'click', function (e) {
                // switch todo status
                e.stopImmediatePropagation();
                var new_state = this.checked ? 'done' : 'open',
                      todo_id = parseInt($(this).val(), 10);
                self.dataset.write(todo_id, {state: new_state}, {}, function () {
                    self.start();
                });
            })
            .delegate('li:not(.oe-done)', 'click', function () {
                self.getParent().getParent().getParent().do_execute_action({
                        type: 'object',
                        name: 'action_launch'
                    }, self.dataset,
                    $(this).data('id'), function () {
                        // after action popup closed, refresh configuration
                        // thingie
                        self.start();
                    });
            });
    }
});

/*
 * Widgets
 * This client action designed to be used as a dashboard widget display
 * the html content of a res_widget given as argument
 */
instance.web.client_actions.add( 'board.home.widgets', 'instance.web_dashboard.Widget');
instance.web_dashboard.Widget = instance.web.View.extend(/** @lends instance.web_dashboard.Widgets# */{
    template: 'HomeWidget',
    /**
     * Initializes a "HomeWidget" client widget: handles the display of a given
     * res.widget objects in an OpenERP view (mainly a dashboard).
     *
     * @constructs instance.web_dashboard.Widget
     * @extends instance.web.View
     *
     * @param {Object} parent
     * @param {Object} options
     * @param {Number} options.widget_id
     */
    init: function (parent, options) {
        this._super(parent);
        this.widget_id = options.widget_id;
    },
    start: function () {
        var ds = new instance.web.DataSet(this, 'res.widget');
        return ds.read_ids([this.widget_id], ['title']).then(this.on_widget_loaded);
    },
    on_widget_loaded: function (widgets) {
        var widget = widgets[0];
        var url = _.str.sprintf(
            '/web_dashboard/widgets/content?session_id=%s&widget_id=%d',
            this.session.session_id, widget.id);
        this.$element.html(QWeb.render('HomeWidget.content', {
            widget: widget,
            url: url
        }));
    }
});

/*
 * HomeTiles this client action display either the list of application to
 * install (if none is installed yet) or a list of root menu items
 */
instance.web.client_actions.add('default_home', 'session.web_dashboard.ApplicationTiles');
instance.web_dashboard.ApplicationTiles = instance.web.OldWidget.extend({
    template: 'web_dashboard.ApplicationTiles',
    init: function(parent) {
        this._super(parent);
    },
    start: function() {
        var self = this;
        var domain = [['application','=',true], ['state','=','installed'], ['name', '!=', 'base']];
        var ds = new instance.web.DataSetSearch(this, 'ir.module.module',{},domain);
        ds.read_slice(['id']).then(function(result) {
            if(result.length) {
                self.on_installed_database();
            } else {
                self.on_uninstalled_database();
            }
        });
    },
    on_uninstalled_database: function() {
        installer = new instance.web_dashboard.ApplicationInstaller(this);
        installer.appendTo(this.$element);
    },
    on_installed_database: function() {
        var self = this;
        self.rpc('/web/menu/get_user_roots', {}).then(function (menu_ids) {
            var menuds = new instance.web.DataSet(this, 'ir.ui.menu',{})
                .read_ids(menu_ids, ['name', 'web_icon_data', 'web_icon_hover_data', 'module']).then(function (applications) {
                    var tiles = QWeb.render('ApplicationTiles.content', {applications: applications});
                    $(tiles).appendTo(self.$element).find('.oe_install-module-link').click(function () {
                        instance.webclient.menu.on_menu_click(null, $(this).data('menu'))
                    });
                });
        });
    }
});

/**
 * ApplicationInstaller
 * This client action  display a list of applications to install.
 */
instance.web.client_actions.add( 'board.application.installer', 'instance.web_dashboard.ApplicationInstaller');
instance.web_dashboard.ApplicationInstaller = instance.web.OldWidget.extend({
    template: 'web_dashboard.ApplicationInstaller',
    start: function () {
        // TODO menu hide
        var r = this._super();
        this.action_manager = new instance.web.ActionManager(this);
        this.action_manager.appendTo(this.$element.find('.oe_installer'));
        this.action_manager.do_action({
            type: 'ir.actions.act_window',
            res_model: 'ir.module.module',
            domain: [['application','=',true]],
            views: [[false, 'kanban']],
            flags: {
                display_title:false,
                search_view: false,
                views_switcher: false,
                action_buttons: false,
                sidebar: false,
                pager: false
            }
        });
        return r;
    },
    destroy: function() {
        this.action_manager.destroy();
        return this._super();
    }
});


};
