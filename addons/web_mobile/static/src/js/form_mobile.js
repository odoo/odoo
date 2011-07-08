openerp.web_mobile.form_mobile = function (openerp) {
openerp.web_mobile.FormView = openerp.base.Controller.extend({
    init: function(session, element_id, list_id, action) {
        this._super(session, element_id);
        this.list_id = list_id;
        this.action = action;
    },
    start: function() {
        var self = this;
        id = this.list_id;
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
                    get_fields = self.get_fields(view_fields);
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
    get_fields: function(view_fields, fields) {
        this.fields = fields || [];
        for (var i=0; i < view_fields.length; i++){
            if (view_fields[i].tag == 'field') {
                this.fields.push(view_fields[i]);
            }
            if (view_fields[i].tag == 'group') {
                this.get_fields(view_fields[i].children, this.fields);
            }
        }
        return this.fields;
    }
});

}