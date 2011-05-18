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
        var $dashboard =  this.$element.find('#dashboard');
        var children = this.node.children;
        
        for(var ch=0; ch < children.length; ch++) {
            var node = children[ch];
            
            var widget;
            if(node.tag.indexOf('child') >= 0) {
                widget = new (openerp.base.form.widgets.get_object('child')) (this.view, node, $dashboard);
            } else {
                //Vpaned
                widget = new (openerp.base.form.widgets.get_object(node.tag)) (this.view, node, $dashboard);
            }
            
            widget.start();
            
        }
        
        jQuery('.column').css('width', 100/children.length+'%');
    },
});


openerp.base.form.Dashbar = openerp.base.form.Widget.extend({
    init: function(view, node, dashboard) {
        this._super(view, node, dashboard);
        this.dashboard = dashboard;
        this.template = 'Portlet'
    },
    start: function() {
        var $dashboard = this.dashboard;
        var children = this.node.children;
        $dashboard.append(QWeb.render(this.template, {widget: this, 'children': children}))
        
        for(var chld=0; chld < children.length;chld++) {
            var child = children[chld];
            var widget = new (openerp.base.form.widgets.get_object(child.tag)) (this.view, child);
            widget.start()
        }
         
        $( ".column" ).sortable({
			connectWith: ".column"
		});
        
        $( ".portlet" ).addClass( "ui-widget ui-widget-content ui-helper-clearfix ui-corner-all" )
			.find( ".portlet-header" )
				.addClass( "ui-widget-header ui-corner-all" )
				.end()
			.find( ".portlet-content" );
            
		$( ".portlet-header .ui-icon" ).click(function() {
			$( this ).toggleClass( "ui-icon-minusthick" ).toggleClass( "ui-icon-plusthick" );
			$( this ).parents( ".portlet:first" ).find( ".portlet-content" ).toggle();
		});

        $( ".column" ).disableSelection();
    }
})

openerp.base.form.Action = openerp.base.form.Widget.extend({
    init: function(view, node) {
        this._super(view, node);
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
        action.flags = {
            search_view : false,
            sidebar : false,
            views_switcher : false,
            action_buttons : false
        }
        var node_attrs = this.node.attrs;
        var content_id = 'portlet-content-'+node_attrs.name;
        var action_manager = new openerp.base.ActionManager(this.session, content_id);
        action_manager.start();
        action_manager.do_action(action);
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
openerp.base.form.widgets.add('child', 'openerp.base.form.Dashbar');
openerp.base.form.widgets.add('vpaned', 'openerp.base.form.Vpaned');
openerp.base.form.widgets.add('action', 'openerp.base.form.Action');
}
