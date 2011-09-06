openerp.base.data_import = function(openerp) {
openerp.base.DataImport = openerp.base.Dialog.extend({
    init: function(parent, dataset){
        this.parent = parent;
        this._super(parent);
        this.dataset = dataset;
    },
    start: function() {
        var self = this;
        self._super(false);
        self.template = 'ImportDataView';
        self.dialog_title = "Import Data"
        self.open({
                    modal: true,
                    width: '70%',
                    height: 'auto',
                    position: 'top',
                    buttons : {
                        "Close" : function() {
                            self.stop();
                          },
                        "Import File" : function() {
                                self.do_import();
                          }
                       },
                    close: function(event, ui){ self.stop();}
                   });
        this.$element.find('#csvfile').change(this.on_autodetect_data);
        this.$element.find('fieldset').change(this.on_autodetect_data);
        this.$element.find('fieldset legend').click(function () {
                $(this).next().toggle();
        });
    },
    do_import: function() {
            var self = this;
            if(!this.$element.find('#csvfile').val()) { return; }
            this.$element.find('#import_data').attr({
                'action': '/base/import/import_data'
            }).ajaxSubmit({
                success: this.on_import_results
            });
    },
    on_autodetect_data: function() {
            var self = this;
            if(this.$element.find("#res td")){
                this.$element.find("#res td").remove();
                this.$element.find("#imported_success").css('display','none');
            }
            if(!this.$element.find('#csvfile').val()) { return; }
            this.$element.find('#import_data').attr({
                'action': '/base/import/detect_data'
            }).ajaxSubmit({
                success: this.on_import_results
            });
    },
    on_import_results:function(res){
        var self = this;
        this.$element.find('#result, #success , #message').empty();

        var results = $.parseJSON(res);
        var result_node = $("#result");
        var records = {};

        if (results['records']){
            records = {'header':results['header'],'sel':results['all_fields'],'row':results['records']};
            result_node.append(QWeb.render('ImportView-result',{'records':records}));
        }else if(results['error']){
            result_node.append(QWeb.render('ImportView-result',{'error': results['error']}));
        }else if(results['success']){
            self.stop();
            this.parent.reload_content();
        }
        this.do_check_req_field(results['req_field']);
        var selected_fields = [];
        $("td #sel_field").click(function(){
            selected_fields = [];
            $("td #sel_field option:selected").each(function(){
                selected_fields.push($(this).index());
            });
        });
        $("td #sel_field").change(function(){
            $("#message").empty();
            $("td #sel_field").css('background-color','');
            $(".ui-button-text:contains('Import File')").parent().attr("disabled",false);
            self.do_check_req_field(results['req_field']);
            var curr_selected = this.selectedIndex;
            if ($.inArray(curr_selected,selected_fields) > -1){
                $(this).css('background-color','#FF6666');
                $("#message").append("*Selected column should not be same.");
                $(".ui-button-text:contains('Import File')").parent().attr("disabled",true);
            }else{
                $(this).css('background-color','');
            }
        });
    },
    do_check_req_field: function(req_fld){
        if (req_fld.length){
            var sel_fields =[];
            var required_fields = [];
            $("td #sel_field option:selected").each(function(){
                sel_fields.push($(this).val());
            });
            _.each(req_fld,function(fld){
                if ($.inArray(fld,sel_fields) <= -1){
                    required_fields.push(fld);
                }
            });
            if (required_fields.length){
                $("#message").append("*Required Fields are not selected which is "+required_fields+". ");
                $(".ui-button-text:contains('Import File')").parent().attr("disabled",true);
            }
        }
    },
    stop: function() {
        $(this.$dialog).remove();
        this._super();
    }
});
};