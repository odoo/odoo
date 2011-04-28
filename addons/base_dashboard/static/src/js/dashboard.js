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
        var board = jQuery('#dashboard').dashboard({
            layoutClass:'layout'
        });
        board.init();
        for(var ch = 0; ch < children.length; ch++) {
            var ch_widgets = children[ch].children;
            for(var chld = 0; chld < ch_widgets.length; chld++) {
                var widget_type = ch_widgets[chld].tag;
                var child_index = widget_type == 'action' ? chld : ch;
                var widget = new (openerp.base.form.widgets.get_object(widget_type)) (this.view, ch_widgets[chld], board, child_index);
                widget.start();
            }
        }
    }
});

openerp.base.form.Action = openerp.base.form.Widget.extend({
    init: function(view, node, board, child_index) {
        this._super(view, node, board, child_index);
        this.board = board;
        this.child_index = child_index;
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
        if(action.search_view)
            action.search_view = false;
        action.no_sidebar = true;
        
        var node_attrs = this.node.attrs;
        var get_column = ['first', 'second', 'third'];
        var board_element = this.board.element.find('[id=column-'+get_column[this.child_index]+']');
        
        this.board.addWidget({
                    'id': node_attrs.name,
                    'title': node_attrs.string,
                }, board_element);
                
        var content_id = node_attrs.name+'-widgetcontent';
        this.board.getWidget(node_attrs.name).element.find('.widgetcontent').attr('id',content_id)
        
        action_manager = new openerp.base.ActionManager(this.session, content_id);
        action_manager.start();
        this.board.getWidget(node_attrs.name).url = action_manager.do_action(action);
    }
})

openerp.base.form.Vpaned = openerp.base.form.Widget.extend({
    init: function(view, node, board, child_index) {
        
        this._super(view, node, board, child_index);
        this.board = board;
        this.child_index = child_index;
    },
    start: function() {
        this._super.apply(this, arguments);
        var children = this.node.children;
        for(var chld=0; chld<children.length; chld++) {
            var ch_widget = children[chld].children;
            for(var ch=0; ch<ch_widget.length; ch++) {
                var widget_type = ch_widget[ch].tag;
                var widget = new (openerp.base.form.widgets.get_object(widget_type)) (this.view, ch_widget[ch], this.board, this.child_index);
                widget.start();
            }
        }
    },
})

openerp.base.form.widgets.add('hpaned', 'openerp.base.form.Board');
openerp.base.form.widgets.add('vpaned', 'openerp.base.form.Vpaned');
openerp.base.form.widgets.add('action', 'openerp.base.form.Action');
}