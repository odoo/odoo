openerp.board = function(instance) {
var QWeb = instance.web.qweb,
    _t = instance.web._t;

if (!instance.board) {
    /** @namespace */
    instance.board = {};
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
        }).bind('sortstop', self.do_save_dashboard);

        // Events
        this.$element.find('.oe_dashboard_link_reset').click(this.on_reset);
        this.$element.find('.oe_dashboard_link_change_layout').click(this.on_change_layout);
        this.$element.find('h2.oe_header span.oe_header_txt').click(function(ev){
            if(ev.target === ev.currentTarget)
                self.on_header_string($(ev.target).parent());
        });
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
    on_header_string:function(h2){
        var self = this;
        var span = h2.find('span:first').hide();
        var input = h2.find('.oe_header_text').css('visibility','visible');
        var attr = h2.closest(".oe_action").data('action_attrs');
        var change_string = function(new_name){
                attr['string'] = new_name;
                span.text(new_name).show();
                input.css('visibility','hidden');
                self.do_save_dashboard();
        }
        input.unbind()
        .val(span.text())
        .change(function(event){
            change_string($(this).val());
        })
        .keyup(function(event){
            if(event.keyCode == 27){
                //esc key to cancel changes
                input.css('visibility','hidden');
                span.show();
            }
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


instance.board.AddToDashboard = instance.web.search.Input.extend({
    template: 'SearchView.addtodashboard',
    _in_drawer: true,
    start: function () {
        var self = this;
        this.$element
            .on('click', 'h4', this.proxy('show_option'))
            .on('submit', 'form', function (e) {
                e.preventDefault();
                self.add_dashboard();
            });
        return this.load_data().then(this.proxy("render_data"));
    },
    load_data:function(){
        var board = new instance.web.Model('board.board');
        return board.call('list');
    },
    _x:function() {
        if (!instance.webclient) { return $.Deferred().reject(); }
        var dashboard_menu = instance.webclient.menu.data.data.children;
        return new instance.web.Model('ir.model.data')
                .query(['res_id'])
                .filter([['name','=','menu_reporting_dashboard']])
                .first().pipe(function (result) {
            var menu = _(dashboard_menu).chain()
                .pluck('children')
                .flatten(true)
                .find(function (child) { return child.id === result.res_id; })
                .value();
            return menu ? menu.children : [];
        });
    },
    render_data: function(dashboard_choices){
        var selection = instance.web.qweb.render(
            "SearchView.addtodashboard.selection", {
                selections: dashboard_choices});
        this.$("input").before(selection)
    },
    add_dashboard: function(){
        var self = this;
        var getParent = this.getParent();
        var view_parent = this.getParent().getParent();
        if (! view_parent.action || ! this.$element.find("select").val()) {
            this.do_warn("Can't find dashboard action");
            return;
        }
        var data = getParent.build_search_data();
        var context = new instance.web.CompoundContext(getParent.dataset.get_context() || []);
        var domain = new instance.web.CompoundDomain(getParent.dataset.get_domain() || []);
        _.each(data.contexts, context.add, context);
        _.each(data.domains, domain.add, domain);
        this.rpc('/board/add_to_dashboard', {
            menu_id: this.$element.find("select").val(),
            action_id: view_parent.action.id,
            context_to_save: context,
            domain: domain,
            view_mode: view_parent.active_view,
            name: this.$element.find("input").val()
        }, function(r) {
            if (r === false) {
                self.do_warn("Could not add filter to dashboard");
            } else {
                self.$element.toggleClass('oe_opened');
                self.do_notify("Filter added to dashboard", '');
            }
        });
    },
    show_option:function(){
        this.$element.toggleClass('oe_opened');
        if (! this.$element.hasClass('oe_opened'))
            return;
        this.$("input").val(this.getParent().fields_view.name || "" );
    }
});


instance.web.SearchView.include({
    add_common_inputs: function() {
        this._super();
        (new instance.board.AddToDashboard(this));

    }
});

};
