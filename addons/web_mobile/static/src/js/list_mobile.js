/*---------------------------------------------------------
 * OpenERP Web Mobile List View
 *---------------------------------------------------------*/

openerp.web_mobile.list_mobile = function (openerp) {

openerp.web_mobile.ListView = openerp.web.Widget.extend({
    init: function(session, element_id, list_id) {
        this._super(session, element_id);
        this.list_id = list_id;
    },
    start: function() {
        this.rpc('/web/menu/action', {'menu_id': this.list_id},
                    this.on_menu_action_loaded);
    },
    on_menu_action_loaded: function(data) {
        var self = this;
        if (data.action.length) {
            this.action = data.action[0][2];
            this.on_search_data();
        }
    },
    on_search_data: function(ev){
        var self = this;
        var dataset = new openerp.base.DataSetStatic(this, this.action.res_model, this.action.context);
        dataset.name_search('', [], 'ilike',false ,function(result){
            self.$element.html(QWeb.render("ListView", {'records' : result}));
            self.$element.find("#header").find('h1').html(self.action.name);
            self.$element.find("a#list-id").click(self.on_list_click);
            self.$element.find("#header").find('#application').click(function(){
                if(!$('#oe_menu').html().length){
                    this.menu = new openerp.web_mobile.Menu(self, "oe_menu");
                    this.menu.start();
                }
                else{
                    self.$element.find("#header").find('#application').attr('href','#oe_menu');
                }
            });
            self.$element.find("#footer").find('#shrotcuts').click(function(){
                this.shortcuts = new openerp.web_mobile.Shortcuts(self, "oe_shortcuts");
                this.shortcuts.start();
            });
            self.$element.find("#footer").find('#preference').click(function(){
                this.options = new openerp.web_mobile.Options(self, "oe_options");
                this.options.start();
            });
            $.mobile.changePage($("#oe_list"), "slide", true, true);
        });
    },
    on_list_click: function(ev) {
        var $record = $(ev.currentTarget);
        var self = this;
        id = $record.data('id');
//        this.header = new openerp.web_mobile.Header(this, "oe_header");
        this.formview = new openerp.web_mobile.FormView(this, "oe_form", id, this.action);
//        this.header.start();
        this.formview.start();
    }
 });
};
