openerp.base_dashboard = function(openerp) {
QWeb.add_template('/base_dashboard/static/src/xml/base_dashboard.xml');
openerp.base.form.Hpaned = openerp.base.form.Widget.extend({
   init: function(view, node) {
        
        this._super(view, node);
        this.template = "Hpaned";
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$element.html(QWeb.render(this.template))
    },
    
    render: function() {
        var self = this;
        jQuery('body').append(
            jQuery('<div>', {'id': 'dashboard_templates'}).hide()
        );
        
        $("#dashboard_templates").load("/base_dashboard/static/src/dashboard_template.html", function(result){
	        self.render_dashboard()
        });
    },
    
    render_dashboard: function() {
        var self = this;
        var data = {"layout": "layout2","data": []}
        var get_column = ['first', 'second', 'third'];
        var children = this.node.children;
        
        var action = []
        for (child in children) {
            action.push({})
            var ch_widget = children[child]['children'];
            for (ch in ch_widget) {
                if (ch_widget[ch].tag == 'action') {
//                    var _act = new openerp.base.form.Action(this.view, ch_widget[ch]);
//                    action[child][ch] = _act.render();
                    data['data'].push({
                        "title": ch_widget[ch].attrs.string,
                        "id": ch_widget[ch].attrs.name,
                        "column": get_column[child],
                        "url": "/base_dashboard/static/data.html",
                        "open": true
                    })
                }
            }
        }
        
        var board = jQuery('#dashboard').dashboard({
           layoutClass:'layout',
           json_data: data
        });
        board.init();
    }
});

openerp.base.form.Action = openerp.base.form.Widget.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "Action";
    },
    start: function() {
        this._super.apply(this, arguments);
    },
    
    render: function(){
        return QWeb.render(this.template, {'node': this.node});
    }
    
});

openerp.base.form.Vpaned = openerp.base.form.Widget.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "Vpaned";
    },
    start: function() {
        this._super.apply(this, arguments);
    },
    
    render: function(){
        return QWeb.render(this.template);
    }
});

}


