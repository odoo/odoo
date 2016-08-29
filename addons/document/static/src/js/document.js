odoo.define('document.document', function(require) {
"use strict";

var core = require('web.core');
var Sidebar = require('web.Sidebar');

var _t = core._t;

Sidebar.include({
    init : function(){
        this._super.apply(this, arguments);
        var view = this.getParent();
        if (view.fields_view && view.fields_view.type === "form") {
            this.sections.splice(1, 0, { 'name' : 'files', 'label' : _t('Attachment(s)'), });
            this.items.files = [];
        }
    },
    on_attachments_loaded: function(attachments) {
        //to display number in name if more then one attachment which has same name.
        var self = this;
        _.chain(attachments)
             .groupBy(function(attachment) { return attachment.name; })
             .each(function(attachment){
                 if(attachment.length > 1)
                     _.map(attachment, function(attachment, i){
                         attachment.name = _.str.sprintf(_t("%s (%s)"), attachment.name, i+1);
                     });
              });
        self._super(attachments);
    },
});

});
