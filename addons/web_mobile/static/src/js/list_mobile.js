/*---------------------------------------------------------
 * OpenERP Web Mobile List View
 *---------------------------------------------------------*/

openerp.web_mobile.list_mobile = function (openerp) {

openerp.web_mobile.ListView = openerp.web.Widget.extend({

    template: 'ListView',

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
            self.$element.html(self.render({'records' : result}));
            self.$element.find("[data-role=header]").find('h1').html(self.action.name);
            self.$element.find("[data-role=header]").find('#home').click(function(){
                $.mobile.changePage("#oe_menu", "slide", false, true);
            });
            self.$element.find("[data-role=footer]").find('#shrotcuts').click(function(){
                if(!$('#oe_shortcuts').html().length){
                    this.shortcuts = new openerp.web_mobile.Shortcuts(self, "oe_shortcuts");
                    this.shortcuts.start();
                }
                else{
                    $.mobile.changePage("#oe_shortcuts", "slide", false, true);
                }
            });
            self.$element.find("[data-role=footer]").find('#preference').click(function(){
                if(!$('#oe_options').html().length){
                    this.options = new openerp.web_mobile.Options(self, "oe_options");
                    this.options.start();
                }
                else{
                    $.mobile.changePage("#oe_options", "slide", false, true);
                }
            });
            self.$element.find("a#list-id").click(self.on_list_click);
            $.mobile.changePage("#"+self.element_id, "slide", false, true);
        });
    },
    on_list_click: function(ev) {
        var $record = $(ev.currentTarget);
        var self = this;
        ev.preventDefault();
        ev.stopPropagation();
        id = $record.data('id');
        head_title = $.trim($record.text());

        if(!$('[id^="oe_form_'+id+this.action.res_model+'"]').html()){
            $('<div id="oe_form_'+id+this.action.res_model+'" data-role="page" data-url="oe_form_'+id+this.action.res_model+'"> </div>').appendTo('#moe');
            this.formview = new openerp.web_mobile.FormView(this, "oe_form_"+id+this.action.res_model, id, this.action, head_title, '' ,'');
            this.formview.start();
        }else{
            $.mobile.changePage('#oe_form_'+id+this.action.res_model, "slide", false, true);
        }
    }
 });
};
