openerp.base_export = function(openerp) {
QWeb.add_template('/base_export/static/src/xml/base_export.xml');
openerp.base.views.add('export', 'openerp.base_export.Export');
openerp.base_export.Export = openerp.base.Controller.extend({

    init: function(session, dataset, views){
        this.dataset = dataset
        this.views = views
        this.session = session
        this._super();

    },
    start: function() {
        this.rpc("/base_export/export/get_fields", {"model": this.dataset.model}, this.on_loaded);
    },
    on_loaded: function(result) {
        var element_id = _.uniqueId("act_window_dialog");
        var self = this;
        var _export = $('<div>', {id: element_id}).dialog({
            title: "Export Data",
            modal: true,
            width: '50%',
            height: 'auto'
        }).html(QWeb.render('ExportTreeView', {'fields': result}))

        jQuery(_export).find('[id^=parentimg_]').click(function(){
            console.log('this>>>id', this.id);
        });
    },
});

};
