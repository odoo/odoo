openerp.web_mobile.list_mobile = function (openerp) {
openerp.web_mobile.ListView = openerp.base.Controller.extend({
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
        var dataset = new openerp.base.DataSetStatic(this.session, this.action.res_model, this.action.context);
        dataset.domain=[['name','ilike',search_val]];
        dataset.name_search(search_val, dataset.domain, 'ilike',false ,function(result){
            self.$element.html(QWeb.render("ListView", {'records' : result.result}));
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
        model = this.action.res_model;
        view_id = this.action.views[1][0];
        this.dataset = new openerp.base.DataSetSearch(this.session, this.action.res_model, null, null);
        this.dataset.read_slice(false, false, false, function(result){
            for (var i = 0; i < result.length; i++) {
                if (result[i].id == id) {
                    var data = result[i];
                }
            }
            self.rpc("/base/formview/load", {"model": model, "view_id": view_id },
                function(result){
                    var view_fields = result.fields_view.arch.children;
                    get_fields = self.filter_fields(view_fields);
                    for (var j = 0; j < view_fields.length; j++) {
                        if (view_fields[j].tag == 'notebook') {
                            var notebooks = view_fields[j];
                        }
                    }
                    jQuery("#oe_header").find("h1").html(result.fields_view.arch.attrs.string);
                    self.$element.html(QWeb.render("FormView", {'get_fields': get_fields, 'notebooks': notebooks || false, 'fields' : result.fields_view.fields, 'values' : data}));
                });
        });
    },
    filter_fields: function(view_fields, fields) {
        this.fields = fields || [];
        for (var i=0; i < view_fields.length; i++){
            if (view_fields[i].tag == 'field') {
                this.fields.push(view_fields[i]);
            }
            if (view_fields[i].tag == 'group') {
                this.filter_fields(view_fields[i].children, this.fields);
            }
        }
        return this.fields;
    }
 });
}