openerp.document = function (instance) {
    _t = instance.web._t;
    instance.web.Sidebar.include({
        init : function(){
            this._super.apply(this, arguments);
            if (this.getParent().view_type == "form"){
                this.sections.splice(1, 0, { 'name' : 'files', 'label' : _t('Attachment(s)'), });
                this.items['files'] = [];
            }
        },
        on_attachments_loaded: function(attachments) {
            //to display number in name if more then one attachment which has same name.
            var self = this;
            _.chain(attachments)
                 .groupBy(function(attachment) { return attachment.name})
                 .each(function(attachment){
                     if(attachment.length > 1)
                         _.map(attachment, function(attachment, i){
                             attachment.name = _.str.sprintf(_t("%s (%s)"), attachment.name, i+1)
                         })
                  })
            self._super(attachments);
        },
    });
};
