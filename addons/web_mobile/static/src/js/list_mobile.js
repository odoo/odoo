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
        var dataset = new openerp.web.DataSetStatic(this, this.action.res_model, this.action.context);
        dataset.name_search('', [], 'ilike',false ,function(result){
            if(self.$element.html().length){
                self.$element.find('[data-role="listview"]').find('li').remove();
                for(var i=0;i<result.length;i++){
                    var newli = '<li><a id="list-id" data-id='+ result[i][0] +' href="#">' + result[i][1] + '</a></li>';  // Create New List Item
                    self.$element.find('[data-role="listview"]').append(newli);
                }
                self.$element.find('[data-role="listview"]').listview('refresh');
            }else{
                self.$element.html(QWeb.render("ListView", {'records' : result}));
                self.$element.find("[data-role=header]").find('h1').html(self.action.name);
                self.$element.find("[data-role=header]").find('#home').click(function(){
                    $.mobile.changePage($("#oe_menu"), "slide", true, true);
                });
                self.$element.find("[data-role=footer]").find('#shortcuts').click(function(){
                    if(!$('#oe_shortcuts').html().length){
                        this.shortcut = new openerp.web_mobile.Shortcuts(self, "oe_shortcuts");
                        this.shortcut.start();
                    }
                    else{
                        $.mobile.changePage($("#oe_shortcuts"), "slide", true, true);
                    }
                });
                self.$element.find("[data-role=footer]").find('#preference').click(function(){
                    if(!$('#oe_options').html().length){
                        this.options = new openerp.web_mobile.Options(self, "oe_options");
                        this.options.start();
                    }
                    else{
                        $.mobile.changePage($("#oe_options"), "slide", true, true);
                    }
                });
            }
            self.$element.find("a#list-id").click(self.on_list_click);
            $.mobile.changePage($("#oe_list"), "slide", true, true);
        });
    },
    on_list_click: function(ev) {
        var $record = $(ev.currentTarget);
        var self = this;
        id = $record.data('id');
        this.formview = new openerp.web_mobile.FormView(this, "oe_form", id, this.action);
        this.formview.start();
    }
 });
};
