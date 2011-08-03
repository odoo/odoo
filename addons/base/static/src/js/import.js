openerp.base.import = function(openerp) {
openerp.base.Import = openerp.base.Dialog.extend({
    init: function(parent, dataset, views){
        this._super(parent);
        this.dataset = dataset;
        this.views = views;
        this.views_id = {};
        for (var key in this.views) {
            this.views_id[key] = this.views[key].view_id
        }
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
                                //$("#import_data").submit();
                                self.do_import();
                          }
                       },
                    close: function(event, ui){ self.stop();}
                   });
        this.$element.find('#csvfile').change(this.on_autodetect_data);
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
        var self = this;
        var results = $.parseJSON(res);

        if (results['records']){
            var result = results['records'];
            if ($('#error').find('table')){
                $("#error table").remove();
            }
            if ($('#records_data').find('tr')){
                $("#records_data tr").remove();
            }
            for (i in result) {
                if (i == 0){
                    $('#records_data').append('<tr class="grid-header"></tr>');
                    for (m in result[i]){
                        $('.grid-header').append('<th class="grid-cell">'+result[i][m]+'</th>');
                    }
                }else{
                    $('#records_data tr:last').after('<tr id='+i+' class="grid-row"></tr>');
                    for (n in result[i]){
                        $("tr[id="+i+"]").append('<td class="grid-cell">'+result[i][n]+'</td>');
                    }
                }
            }
        }else if(results['error']){
            var result = results['error'];
            if ($('#records_data').find('tr')){
                $("#records_data tr").remove();
            }
            if ($('#error').find('table')){
                $("#error table").remove();
            }
            $("#error").append('<table id="error_tbl"><tr style="white-space: pre-line;">The import failed due to:'+result['message']+'</tr></table>');
            if (result['preview']){
                $("#error_tbl tr:last").after('<tr>Here is a preview of the file we could not import:</tr>');
                $("#error_tbl tr:last").after('<tr><pre>'+result['preview']+'</pre></tr>');
            }
        }else if(results['success']){
            var result = results['success'];
            $("#imported_success").css('display','block');
            $("#res").append('<td>'+result['message']+'</td>')
        }
    },
    stop: function() {
        $(this.$dialog).remove();
        this._super();
    },
});
}