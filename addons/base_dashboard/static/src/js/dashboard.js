openerp.base_dashboard = function(openerp){

QWeb.add_template('/base_dashboard/static/src/xml/base_dashboard.xml');

openerp.base.form.Board = openerp.base.form.Widget.extend({
    init: function(view, node) {
        
        this._super(view, node);
        this.template = "Board";
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element.html(QWeb.render(this.template));  
    },
    
    render: function() {
        var self = this;
        jQuery('body').append(
            jQuery('<div>', {'id': 'dashboard_template'}).load('/base_dashboard/static/src/dashboard_template.html',self.on_loaded).hide()
        )
        
    },
    
    on_loaded: function() {
        var children = this.node.children;
        var get_column = ['first', 'second', 'third'];
        var board = jQuery('#dashboard').dashboard({
            layoutClass:'layout'
        });
        board.init();
        for(var ch = 0; ch < children.length; ch++) {
            var ch_widgets = children[ch].children;
            for(var chld = 0; chld < ch_widgets.length; chld++) {
                var widget_type = ch_widgets[chld].tag;
                var board_element = board.element.find('[id=column-'+get_column[chld]+']');
                var widget = new (openerp.base.form.widgets.get_object(widget_type)) (this.view, ch_widgets[chld], board_element);
                board.addWidget({
                    'id': ch_widgets[chld].attrs.name,
                    'title': ch_widgets[chld].attrs.string,
                    'url': widget.start()
                }, board_element)
            }
        }
    }
});

openerp.base.form.Action = openerp.base.form.Widget.extend({
    init: function(view, node, column) {
        this._super(view, node, column);
        this.template = "Action";
    },
    start: function() {
        this._super.apply(this, arguments);
        this.rpc('/base_dashboard/dashboard/load',{
            node_attrs: this.node.attrs
        },
        this.on_load_action);
    },
    
    on_load_action: function(result) {
        var action = result.action;
        action_manager = new openerp.base.ActionManager(this.session, this.$element.attr('id'));
        action_manager.start();
        action_manager.do_action(action);
    }
})

openerp.base.form.widgets.add('hpaned', 'openerp.base.form.Board');
openerp.base.form.widgets.add('action', 'openerp.base.form.Action');
}