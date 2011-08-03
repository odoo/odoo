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
                                $("#import_data").submit();
                                //self.do_import();
                          }
                       },
                    close: function(event, ui){ self.stop();}
                   });
    },
});
}