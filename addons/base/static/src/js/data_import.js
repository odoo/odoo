openerp.base.data_import = function(openerp) {
openerp.base.DataImport = openerp.base.Dialog.extend({
    init: function(parent, dataset){
        this._super(parent);
        this.dataset = dataset;
    },
    start: function() {
        var self = this
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
                success: this.import_results
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
                success: this.import_results
            });
    },
    import_results:function(res){
        $('#result, #success').empty();

        var results = $.parseJSON(res);
        var result_node = $("#result");
        if (results['records']){
            records = {'header':results['header'],'sel':results['all_fields'],'row':results['records']};
            result_node.append(QWeb.render('ImportView-result',{'records':records}));
        }else if(results['error']){
            result_node.append(QWeb.render('ImportView-result',{'error': results['error']}));
        }else if(results['success']){
            var success_node = $("#success");
            success_node.append(QWeb.render('ImportView-result',{'success': results['success']}));
        }
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
            var curr_selected = this.selectedIndex;
            if ($.inArray(curr_selected,selected_fields) > -1){
                $(this).css('background-color','#FF6666');
                $("#message").append("Selected column should not be same.");
                $(".ui-button-text:contains('Import File')").parent().attr("disabled",true);
            }else{
                $(this).css('background-color','');
            }
        });
    },
    stop: function() {
        $(this.$dialog).remove();
        this._super();
    }
});
};