openerp.base_dashboard = function(openerp) {

QWeb.add_template('/base_dashboard/static/src/xml/base_dashboard.xml');

openerp.base.form.DashBoard = openerp.base.form.Widget.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "DashBoard";
    },
    start: function() {
        var self = this;
        this._super.apply(this, arguments);
        this.$element.find(".oe-dashboard-column").sortable({
            connectWith: ".oe-dashboard-column",
            scroll: false
        }).disableSelection().bind('sortstop', self.do_save_dashboard);
        this.$element.find('.oe-dashboard-link-add_widget').click(this.on_add_widget);
        this.$element.find('.oe-dashboard-link-edit_layout').click(this.on_edit_layout);

        this.$element.find('.oe-dashboard-column .ui-icon-minusthick').click(function() {
            $(this).toggleClass('ui-icon-minusthick').toggleClass('ui-icon-plusthick');
            $(this).parents('.oe-dashboard-action:first .oe-dashboard-action-content').toggle();
        });

        $('.oe-dashboard-column .ui-icon-closethick').click(function() {
            $(this).parents('.oe-dashboard-action:first').remove();
            self.do_save_dashboard();
        });

        this.actions_attrs = {};
        // Init actions
        _.each(this.node.children, function(column) {
            _.each(column.children, function(action) {
                delete(action.attrs.width);
                delete(action.attrs.height);
                delete(action.attrs.colspan);
                self.actions_attrs[action.attrs.name] = action.attrs;
                self.rpc('/base/action/load', {
                    action_id: parseInt(action.attrs.name, 10)
                }, self.on_load_action);
            });
        });
    },
    on_add_widget: function() {
    },
    on_edit_layout: function() {
    },
    do_save_dashboard: function() {
        var self = this;
        var board = {
                style : this.$element.find('.oe-dashboard').attr('data-layout'),
                columns : []
            };
        this.$element.find('.oe-dashboard-column').each(function() {
            var actions = [];
            $(this).find('.oe-dashboard-action').each(function() {
                var action_id = $(this).attr('data-id');
                actions.push(self.actions_attrs[action_id]);
            });
            board.columns.push(actions);
        });
        var xml = QWeb.render('DashBoard.xml', board);
    },
    on_load_action: function(result) {
        var action = result.result;
        action.flags = {
            search_view : false,
            sidebar : false,
            views_switcher : false,
            action_buttons : false,
            pager: false
        }
        var element_id = this.view.element_id + '_action_' + action.id;
        var view = new openerp.base.ViewManagerAction(this.session, element_id, action);
        view.start();
    },
    render: function() {
        return QWeb.render(this.template, this);
    }
});
openerp.base.form.DashBoardLegacy = openerp.base.form.DashBoard.extend({
    render: function() {
        if (this.node.tag == 'hpaned') {
            this.node.attrs.style = '1-1';
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
        return QWeb.render(this.template, this);
    }
});

openerp.base.form.widgets.add('hpaned', 'openerp.base.form.DashBoardLegacy');
openerp.base.form.widgets.add('vpaned', 'openerp.base.form.DashBoardLegacy');
openerp.base.form.widgets.add('board', 'openerp.base.form.DashBoard');
}
