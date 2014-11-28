openerp.board = function(instance) {
var QWeb = instance.web.qweb,
    _t = instance.web._t;

if (!instance.board) {
    /** @namespace */
    instance.board = {};
}

instance.web.form.DashBoard = instance.web.form.FormWidget.extend({
    events: {
        'click .oe_dashboard_link_change_layout': 'on_change_layout',
        'click h2.oe_header span.oe_header_txt': function (ev) {
            if(ev.target === ev.currentTarget)
                this.on_header_string($(ev.target).parent());
        },
        'click .oe_dashboard_column .oe_fold': 'on_fold_action',
        'click .oe_dashboard_column .oe_close': 'on_close_action',
    },
    init: function(view, node) {
        this._super(view, node);
        this.form_template = 'DashBoard';
        this.actions_attrs = {};
        this.action_managers = [];
    },
    start: function() {
        var self = this;
        this._super.apply(this, arguments);

        this.$('.oe_dashboard_column').sortable({
            connectWith: '.oe_dashboard_column',
            handle: '.oe_header',
            scroll: false
        }).bind('sortstop', self.do_save_dashboard);

        var old_title = this.__parentedParent.get('title');
        this.__parentedParent.on('load_record', self, function(){
            self.__parentedParent.set({ 'title': old_title});
        });

        // Init actions
        _.each(this.node.children, function(column, column_index) {
            _.each(column.children, function(action, action_index) {
                delete(action.attrs.width);
                delete(action.attrs.height);
                delete(action.attrs.colspan);
                var action_id = _.str.toNumber(action.attrs.name);
                if (!_.isNaN(action_id)) {
                    self.rpc('/web/action/load', {action_id: action_id}).done(function(result) {
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
    on_change_layout: function() {
        var self = this;
        var qdict = {
            current_layout : this.$el.find('.oe_dashboard').attr('data-layout')
        };
        var $dialog = new instance.web.Dialog(this, {
                            title: _t("Edit Layout"),
                        }, QWeb.render('DashBoard.layouts', qdict)).open();
        $dialog.$el.find('li').click(function() {
            var layout = $(this).attr('data-layout');
            self.do_change_layout(layout);
            $dialog.$dialog_box.modal('hide'); 
        });
    },
    do_change_layout: function(new_layout) {
        var $dashboard = this.$el.find('.oe_dashboard');
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
                style : this.$el.find('.oe_dashboard').attr('data-layout'),
                columns : []
            };
        this.$el.find('.oe_dashboard_column').each(function() {
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
        });
    },
    on_load_action: function(result, index, action_attrs) {
        var self = this,
            action = result,
            view_mode = action_attrs.view_mode;

        // evaluate action_attrs context and domain
        action_attrs.context_string = action_attrs.context;
        action_attrs.context = instance.web.pyeval.eval(
            'context', action_attrs.context || {});
        action_attrs.domain_string = action_attrs.domain;
        action_attrs.domain = instance.web.pyeval.eval(
            'domain', action_attrs.domain || [], action_attrs.context);
        if (action_attrs.context['dashboard_merge_domains_contexts'] === false) {
            // TODO: replace this 6.1 workaround by attribute on <action/>
            action.context = action_attrs.context || {};
            action.domain = action_attrs.domain || [];
        } else {
            action.context = instance.web.pyeval.eval(
                'contexts', [action.context || {}, action_attrs.context]);
            action.domain = instance.web.pyeval.eval(
                'domains', [action_attrs.domain, action.domain || []],
                action.context)
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
            headless: true,
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
        if (am.inner_widget) {
            var new_form_action = function(id, editable) {
                var new_views = [];
                _.each(action_orig.views, function(view) {
                    new_views[view[1] === 'form' ? 'unshift' : 'push'](view);
                });
                if (!new_views.length || new_views[0][1] !== 'form') {
                    new_views.unshift([false, 'form']);
                }
                action_orig.views = new_views;
                action_orig.res_id = id;
                action_orig.flags = {
                    form: {
                        "initial_mode": editable ? "edit" : "view",
                    }
                };
                self.do_action(action_orig);
            };
            var list = am.inner_widget.views.list;
            if (list) {
                list.created.done(function() {
                    $(list.controller.groups).off('row_link').on('row_link', function(e, id) {
                        new_form_action(id);
                    });
                });
            }
            var kanban = am.inner_widget.views.kanban;
            if (kanban) {
                kanban.created.done(function() {
                    kanban.controller.open_record = function(id, editable) {
                        new_form_action(id, editable);
                    };
                });
            }
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
        this.$el.html(rendered);
    },
    no_result: function() {
        if (this.view.options.action.help) {
            this.$el.append(
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
            this.node.attrs.layout = '2-1';
        } else if (this.node.tag == 'vpaned') {
            this.node.attrs.layout = '1';
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


instance.web.search.FavoriteMenu.include({
    prepare_dropdown_menu: function (filters) {
        var self = this;
        this._super(filters);
        this.$('.favorites-menu').append(QWeb.render('SearchView.addtodashboard'));
        var $add_to_dashboard = this.$('.add-to-dashboard');
        this.$add_dashboard_btn = $add_to_dashboard.eq(2).find('button');
        this.$add_dashboard_input = $add_to_dashboard.eq(1).find('input');
        this.$add_dashboard_link = $add_to_dashboard.first().find('a');
        var title = this.searchview.getParent().title;
        this.$add_dashboard_input.val(title);
        this.$add_dashboard_link.click(function () {
            self.toggle_dashboard_menu();
        });
        this.$add_dashboard_btn.click(this.proxy('add_dashboard'));
    },
    toggle_dashboard_menu: function (is_open) {
        this.$add_dashboard_link
            .toggleClass('closed-menu', !is_open)
            .toggleClass('open-menu', is_open);
        this.$add_dashboard_btn.toggle(is_open);
        this.$add_dashboard_input.toggle(is_open);
        if (this.$add_dashboard_link.hasClass('open-menu')) {
            this.$add_dashboard_input.focus();
        }
    },
    close_menus: function () {
        this.toggle_dashboard_menu(false);
        this._super();
    },
    add_dashboard: function () {
        var self = this,
            view_manager = this.findAncestor(function (a) {
                return a instanceof instance.web.ViewManager
            });
        if (!view_manager.action) {
            this.do_warn(_t("Can't find dashboard action"));
            return;
        }
        var searchview = view_manager.searchview,
            data = searchview.build_search_data(),
            context = new instance.web.CompoundContext(searchview.dataset.get_context() || []),
            domain = new instance.web.CompoundDomain(searchview.dataset.get_domain() || []);
        _.each(data.contexts, context.add, context);
        _.each(data.domains, domain.add, domain);

        context.add({
            group_by: instance.web.pyeval.eval('groupbys', data.groupbys || [])
        });
        var c = instance.web.pyeval.eval('context', context);
        for(var k in c) {
            if (c.hasOwnProperty(k) && /^search_default_/.test(k)) {
                delete c[k];
            }
        }
        this.toggle_dashboard_menu(false);
        c.dashboard_merge_domains_contexts = false;
        var d = instance.web.pyeval.eval('domain', domain),
            board = new instance.web.Model('board.board'),
            name = self.$add_dashboard_input.val();
        
        board.call('list', [board.context()])
            .then(function (board_list) {
                return self.rpc('/board/add_to_dashboard', {
                    menu_id: board_list[0].id,                    
                    action_id: view_manager.action.id,
                    context_to_save: c,
                    domain: d,
                    view_mode: view_manager.active_view.type,
                    name: name,
                });
            }).then(function (r) {
                if (r) {
                    self.do_notify(_.str.sprintf(_t("'%s' added to dashboard"), name), '');
                } else {
                    self.do_warn(_t("Could not add filter to dashboard"));
                }
            });
    },
});

};
