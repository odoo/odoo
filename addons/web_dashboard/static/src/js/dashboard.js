openerp.web_dashboard = function(instance) {
var QWeb = instance.web.qweb,
    _t = instance.web._t;

if (!instance.web_dashboard) {
    /** @namespace */
    instance.web_dashboard = {};
}

instance.web.form.DashBoard = instance.web.form.FormWidget.extend({
    init: function(view, node) {
        this._super(view, node);
        this.form_template = 'DashBoard';
        this.actions_attrs = {};
        this.action_managers = [];
    },
    start: function() {
        var self = this;
        this._super.apply(this, arguments);

        this.$element.find('.oe_dashboard_column').sortable({
            connectWith: '.oe_dashboard_column',
            handle: '.oe_header',
            scroll: false
        }).disableSelection().bind('sortstop', self.do_save_dashboard);

        // Events
        this.$element.find('.oe_dashboard_link_reset').click(this.on_reset);
        this.$element.find('.oe_dashboard_link_change_layout').click(this.on_change_layout);

        this.$element.delegate('.oe_dashboard_column .oe_fold', 'click', this.on_fold_action);
        this.$element.delegate('.oe_dashboard_column .oe_close', 'click', this.on_close_action);

        // Init actions
        _.each(this.node.children, function(column, column_index) {
            _.each(column.children, function(action, action_index) {
                delete(action.attrs.width);
                delete(action.attrs.height);
                delete(action.attrs.colspan);
                var action_id = _.str.toNumber(action.attrs.name);
                if (!_.isNaN(action_id)) {
                    self.rpc('/web/action/load', {action_id: action_id}, function(result) {
                        self.on_load_action(result, column_index + '_' + action_index, action.attrs);
                    });
                }
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
            current_layout : this.$element.find('.oe_dashboard').attr('data-layout')
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
        var $dashboard = this.$element.find('.oe_dashboard');
        var current_layout = $dashboard.attr('data-layout');
        if (current_layout != new_layout) {
            var clayout = current_layout.split('-').length,
                nlayout = new_layout.split('-').length,
                column_diff = clayout - nlayout;
            if (column_diff > 0) {
                var $last_column = $();
                $dashboard.find('.oe_dashboard_column').each(function(k, v) {
                    if (k >= nlayout) {
                        $(v).find('.oe_action').appendTo($last_column);
                    } else {
                        $last_column = $(v);
                    }
                });
            }
            $dashboard.toggleClass('oe_dashboard_layout_' + current_layout + ' oe_dashboard_layout_' + new_layout);
            $dashboard.attr('data-layout', new_layout);
            this.do_save_dashboard();
        }
    },
    on_fold_action: function(e) {
        var $e = $(e.currentTarget),
            $action = $e.parents('.oe_action:first'),
            id = parseInt($action.attr('data-id'), 10);
        if ($e.is('.oe_minimize')) {
            $action.data('action_attrs').fold = '1';
        } else {
            delete($action.data('action_attrs').fold);
        }
        $e.toggleClass('oe_minimize oe_maximize');
        $action.find('.oe_content').toggle();
        this.do_save_dashboard();
    },
    on_close_action: function(e) {
        if (confirm(_t("Are you sure you want to remove this item ?"))) {
            $(e.currentTarget).parents('.oe_action:first').remove();
            this.do_save_dashboard();
        }
    },
    do_save_dashboard: function() {
        var self = this;
        var board = {
                form_title : this.view.fields_view.arch.attrs.string,
                style : this.$element.find('.oe_dashboard').attr('data-layout'),
                columns : []
            };
        this.$element.find('.oe_dashboard_column').each(function() {
            var actions = [];
            $(this).find('.oe_action').each(function() {
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
            self.$element.find('.oe_dashboard_link_reset').show();
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
            action.views = _.map(view_mode.split(','), function(mode) {
                mode = mode === 'tree' ? 'list' : mode;
                return _(action.views).find(function(view) { return view[1] == mode; })
                    || [false, mode];
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
        if (am.inner_widget) {
            am.inner_widget.on_mode_switch.add(function(mode) {
                var new_views = [];
                _.each(action_orig.views, function(view) {
                    new_views[view[1] === mode ? 'unshift' : 'push'](view);
                });
                if (!new_views.length || new_views[0][1] !== mode) {
                    new_views.unshift([false, mode]);
                }
                action_orig.views = new_views;
                action_orig.res_id = am.inner_widget.dataset.ids[am.inner_widget.dataset.index];
                self.do_action(action_orig);
            });
        }
    },
    renderElement: function() {
        this._super();

        var check = _.detect(this.node.children, function(column, column_index) {
            return _.detect(column.children,function(element){
                return element.tag === "action"? element: false;
            });
        });
        if (!check) {
            return this.no_result();
        }
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
    no_result: function() {
        if (this.view.options.action.help) {
            this.$element.append(
                $('<div class="oe_view_nocontent">')
                    .append($('<img>', { src: '/web_dashboard/static/src/img/view_todo_arrow.png' }))
                    .append($('<div>').html(this.view.options.action.help || " "))
            );
        }
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


};
