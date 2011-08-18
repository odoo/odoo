/*---------------------------------------------------------
 * OpenERP Web Mobile List View
 *---------------------------------------------------------*/

openerp.web_mobile.list_mobile = function (openerp) {

openerp.web_mobile.ListView = openerp.base.Widget.extend({
    init: function(session, element_id, list_id) {
        this._super(session, element_id);
        this.list_id = list_id;
    },
    start: function() {
        this.rpc('/base/menu/action', {'menu_id': this.list_id},
                    this.on_menu_action_loaded);
    },
    on_menu_action_loaded: function(data) {
        var self = this;
        if (data.action.length) {
            this.action = data.action[0][2];
            this.on_search_data('');
        }
    },
    on_search_data: function(request){
        if(request){
            if(request.term){
                var search_val = request.term;
            }else{
                if(request.which==27 || request.which==13 || request.which==9){
                    var search_val = '';
                }else if(request.which==38 || request.which==40 || request.which==39 || request.which==37){
                    return;
                }else if($("#searchid").val()==""){
                    var search_val = '';
                }else{
                    return;
                }
            }
        }
        else{
            var search_val = '';
        }
        var self = this;

        var dataset = new openerp.base.DataSetStatic(this, this.action.res_model, this.action.context);
        dataset.domain=[['name','ilike',search_val]];
        dataset.name_search(search_val, dataset.domain, 'ilike',false ,function(result){
            self.$element.html(QWeb.render("ListView", {'records' : result}));
            self.$element.find("#searchid").focus();
            if(request.term){
                self.$element.find("#searchid").val(request.term);
            }
            self.$element.find("#searchid").autocomplete({
                source: function(req) { self.on_search_data(req); },
                focus: function(e, ui) {
                    e.preventDefault();
                },
                html: true,
                minLength: 0,
                delay: 0
            });
            self.$element.find("#searchid").keyup(self.on_search_data);
            self.$element.find("a#list-id").click(self.on_list_click);
        });
    },
    on_list_click: function(ev) {
        $record = $(ev.currentTarget);
        var self = this;
        id = $record.data('id');
        this.formview = new openerp.web_mobile.FormView(this, "oe_app", id, this.action);
        this.formview.start();
    }
 });
}