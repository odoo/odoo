/*---------------------------------------------------------
 * OpenERP Web Mobile List View
 *---------------------------------------------------------*/

openerp.web_mobile.list_mobile = function (instance) {

instance.web_mobile.ListView = instance.web_mobile.MobileWidget.extend({

    template: 'ListView',

    init: function(session, element_id, list_id) {
        this._super(session, element_id);
        this.list_id = list_id;
    },
    start: function() {
        this.rpc('/web/menu/action', {'menu_id': this.list_id}, this.on_menu_action_loaded);
    },
    on_menu_action_loaded: function(data) {
        var self = this;
        if (data.action.length) {
            this.action = data.action[0][2];
            return this.rpc('/web/listview/load', {
                model: this.action.res_model,
                view_id: this.action.views[0][0],
                view_type: "tree",
                context: this.action.context,
                toolbar: false
            }, this.on_search_data);
        }
    },
    on_search_data: function(ev){
        var self = this;
        var list_ids = [];
        var datasearch = new instance.web.DataSetSearch(self, self.action.res_model,self.action.context);
        datasearch.domain = self.action.domain;
        datasearch.read_slice(['name'], {context:datasearch.context, domain: datasearch.domain, limit:80}).then(function(listresult){
            _.each(listresult, function(i) {
                list_ids.push(i.id);
            });
            _.extend(self.action.context,{"html_name_get" : true});
            var dataset = new instance.web.DataSet(self, datasearch.model,datasearch.context);
            dataset.name_get(list_ids,function(res){
                var additional = "";
                if(res['html_name_get']){
                    additional = res['display'];
                }
                self.$element.html(self.render({'records': res, 'data': additional }));
                self.$element.find("[data-role=header]").find('h1').html(self.action.name);
                self.$element.find("[data-role=header]").find('#home').click(function(){
                    $.mobile.changePage("#oe_menu", "slide", false, true);
                });
                self.$element.find("a#list-id").click(self.on_list_click);
                $.mobile.changePage("#"+self.element_id, "slide", false, true);
                self.$element.find("a#list-id").find('span').addClass('desc');
            });
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
            this.formview = new instance.web_mobile.FormView(this, "oe_form_"+id+this.action.res_model, id, this.action, head_title, '' ,'');
            this.formview.start();
        }else{
            $.mobile.changePage('#oe_form_'+id+this.action.res_model, "slide", false, true);
        }
    }
 });
};
