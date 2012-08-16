/*---------------------------------------------------------
 * OpenERP Web Mobile Form View
 *---------------------------------------------------------*/

openerp.web_mobile.form_mobile = function (instance) {

instance.web_mobile.FormView = instance.web_mobile.MobileWidget.extend({

    template: 'FormView',

    init: function(session, element_id, list_id, action, head_title, resmodel, viewid) {
        this._super(session, element_id);
        this.list_id = list_id;
        this.action = action;
        this.head_title = head_title;
        this.resmodel = resmodel;
        this.viewid = viewid;
    },
    start: function() {
        var self = this;
        var id = this.list_id;
        var model = this.action.res_model || this.resmodel;
        if(this.action){
            var view_id = this.action.views[1][0];
        }else{
            var view_id = this.viewid;
        }
        this.dataset = new instance.web.DataSetSearch(this, model, null, null);
        var context = new instance.web.CompoundContext(this.dataset.get_context());
        this.dataset.read_slice([]).then(function (result) {
            for (var i = 0; i < result.length; i++) {
                if (result[i].id == id) {
                    self.datarecord = result[i];
                }
            }
            self.rpc("/web/view/load", {"model": model, "view_id": view_id, "view_type": "form", context: context}, self.on_loaded)
        });
    },
    on_loaded: function(result) {
        var self = this;
        var fields = result.fields;
        var view_fields = result.arch.children;
        var get_fields = this.get_fields(view_fields);
        var values = self.datarecord;
        for (var j = 0; j < view_fields.length; j++) {
            if (view_fields[j].tag == 'notebook') {
                var notebooks = view_fields[j];
            }
        }
        self.hidden_fields(get_fields,fields);
        self.$element.html(self.render({'get_fields': get_fields, 'notebooks': notebooks || false, 'fields' : fields, 'values' : values ,'temp_flag':'1'}));
        self.$element.find("[data-role=header]").find('h1').html(self.head_title);
        self.$element.find("[data-role=header]").find('#home').click(function(){
            $.mobile.changePage("#oe_menu", "slide", false, true);
        });
        self.$element.find('[data-role=collapsible-set]').find('[data-role=collapsible]').each(function(i){
            for (var k = 0; k < notebooks.children.length; k++) {
                if (notebooks.children[k].attrs.string == $(this).attr('id')) {
                    get_fields_notebook = self.get_fields(notebooks.children[k].children);
                    self.hidden_fields(get_fields_notebook,fields);
                    $(this).find('div#page_content').html(self.render({'get_fields': get_fields_notebook,'fields' : fields, 'values' : values}));
                }
            }
        });
        self.$element.find('#o2m_m2m').click(function(ev) {
            ev.preventDefault();
            ev.stopPropagation();
            var relational = $(this).attr('for');
            var rel_field = fields[relational];
            var rel_ids = values[relational];
            var head = rel_field.string;
            if (rel_ids) {
                var list_ids = [];
                var datasearch = new instance.web.DataSetSearch(self, rel_field.relation, rel_field.context);
                datasearch.domain=[['id', 'in', rel_ids]];
                datasearch.read_slice(['name'], {context:rel_field.context, domain: datasearch.domain, limit:80}).then(function(listrec){
                    _.each(listrec, function(i) {
                        list_ids.push(i.id);
                    });
                    _.extend(rel_field.context,{"html_name_get" : true});
                    var dataset = new instance.web.DataSet(self, rel_field.relation,rel_field.context);
                    dataset.name_get(list_ids,function(res){
                        var additional = "";
                        if(res['html_name_get']){
                            additional = res['display'];
                        }
                        if(!$('[id^="oe_list_'+relational+'_'+self.element_id+'"]').html()){
                            $('<div id="oe_list_'+relational+'_'+self.element_id+'" data-role="page" data-url="oe_list_'+relational+'_'+self.element_id+'"> </div>').appendTo('#moe');
                            $('[id^="oe_list_'+relational+'_'+self.element_id+'"]').html(instance.web.qweb.render("ListView", {'records' : res,'data': additional}));
                            $('[id^="oe_list_'+relational+'_'+self.element_id+'"]').find("[data-role=header]").find('h1').html(head);
                            $('[id^="oe_list_'+relational+'_'+self.element_id+'"]').find("[data-role=header]").find('#home').click(function(){
                                $.mobile.changePage("#oe_menu", "slide", false, true);
                            });
                            $('[id^="oe_list_'+relational+'_'+self.element_id+'"]').find("a#list-id").click(function(ev){
                                ev.preventDefault();
                                ev.stopPropagation();
                                var head_title = $(this).text();
                                var listid = $(ev.currentTarget).data('id');
                                if(!$('[id^="oe_form_'+listid+rel_field.relation+'"]').html()){
                                    $('<div id="oe_form_'+listid+rel_field.relation+'" data-role="page" data-url="oe_form_'+listid+rel_field.relation+'"> </div>').appendTo('#moe');
                                        this.formview = new instance.web_mobile.FormView(self, "oe_form_"+listid+rel_field.relation, listid, '', head, rel_field.relation, false);
                                        this.formview.start();
                                }else{
                                    $.mobile.changePage('#oe_form_'+listid+rel_field.relation, "slide", false, true);
                                }
                            });
                            $.mobile.changePage("#oe_list_"+relational+"_"+self.element_id, "slide", false, true);
                            $('[id^="oe_list_'+relational+'_'+self.element_id+'"]').find("a#list-id").find('span').addClass('desc');
                        }else{
                            $.mobile.changePage("#oe_list_"+relational+"_"+self.element_id, "slide", false, true);
                        }
                    });
                });
            }
        });
        self.$element.find('#m2o_btn').click(this.open_m2o_form);
        $.mobile.changePage("#"+self.element_id, "slide", false, true);
        self.formatdata('', '', '', '',self.element_id,'slider');
    },
    open_m2o_form : function(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var head = $(this).find('a').attr('name');
        var selected_id = $(this).find('a').attr('value');
        var select_model = $(this).attr('for');
        if(selected_id){
            if(!$('[id^="oe_form_'+selected_id+select_model+'"]').html()){
                $('<div id="oe_form_'+selected_id+select_model+'" data-role="page" data-url="oe_form_'+selected_id+select_model+'"> </div>').appendTo('#moe');
                    this.formview = new instance.web_mobile.FormView(self, "oe_form_"+selected_id+select_model, selected_id, '', head, select_model, false);
                    this.formview.start();
            }else{
                $.mobile.changePage('#oe_form_'+selected_id+select_model, "slide", false, true);
            }
        }
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
            if (view_fields[i].tag == 'level') {
                this.get_fields(view_fields[i].children, this.fields);
            }
            if (view_fields[i].tag == 'page') {
                this.get_fields(view_fields[i].children, this.fields);
            }
        }
        return this.fields;
    },
    formatdata: function(getfields, fields, result, data, id, flag){
        if(flag == "element") {
            for(var i = 0; i < getfields.length; i++) {
                if (getfields[i].attrs.widget == "progressbar") {
                    $("#progress").progressbar({value: data[getfields[i].attrs.name]})
                }
                $('[id^="'+id+'"]').find('input').each(function() {
                    // Set Date and Datetime field for main form
                    if($(this).attr('id') == getfields[i].attrs.name) {
                        if(fields[getfields[i].attrs.name].type == "date") {
                            $("#"+getfields[i].attrs.name).datepicker();
                        }else if(fields[getfields[i].attrs.name].type == "datetime" || fields[getfields[i].attrs.name].type == "time") {
                            $("#"+getfields[i].attrs.name).datetimepicker();
                        }
                        // Temp: Set as disabled
                        $("#"+getfields[i].attrs.name).attr('disabled', 'true');
                        if(result.fields[getfields[i].attrs.name]){
                            var dateresult = instance.web.format_value(data[getfields[i].attrs.name], {"widget": result.fields[getfields[i].attrs.name].type});
                            $(this).val(dateresult);
                        }
                    }
                    $('[id^="'+id+'"]').find('#website').each(function(){
                        $(this).css('display','inline-block');
                        $(this).css('width','60%');
                    });
                    $('[id^="'+id+'"]').find('#email').each(function(){
                        $(this).css('display','inline-block');
                        $(this).css('width','60%');
                    });
                    $('[id^="'+id+'"]').find('#email_from').each(function(){
                        $(this).css('display','inline-block');
                        $(this).css('width','60%');
                    });
                });
                // Temp: Selection set as disabled
                $('[id^="'+id+'"]').find('select').each(function() {
                    $(this).find('option').attr('disabled', 'true')
                });
            }
        }
        if(flag == "slider") {
            $('[id^="'+id+'"]').find('#slider').each(function() {
                $(this).slider({ disabled: "true" });
            });
            $('[id^="'+id+'"]').find('.ui-selectmenu').each(function(){
                $(this).click(function() {
                    $(this).css('top', '-9999px');
                    $(this).css('left', '-9999px');
                });
            });
        }
    },
    hidden_fields: function(get_fields, fields) {
        for(var i=0;i<get_fields.length;i++){
            if(get_fields[i].attrs.invisible){
                fields[get_fields[i].attrs.name].type='hidden';
            }
        }
    }
});

};
