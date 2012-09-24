openerp.document = function (instance) {
    _t = instance.web._t;
    instance.web.SidebarAttachement =instance.web.Sidebar.include({
        init : function(){
            this._super.apply(this, arguments);
            this.sections.unshift({ 'name' : 'files', 'label' : _t('Attachment(s)'), });
            this.items['files'] = [];
        }
    });
};