openerp.base.tree = function(openerp) {
openerp.base.views.add('tree', 'openerp.base.TreeView');
openerp.base.TreeView = openerp.base.View.extend({
    init: function(view_manager, session, element_id, dataset, view_id, options) {
        this._super(session, element_id);
        this.view_manager = view_manager || new openerp.base.NullViewManager();
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;

        this.columns = [];

        this.options = _.extend({}, this.defaults, options || {});
        this.flags =  this.view_manager.action.flags;
    },
    start: function () {
        this._super();
        return this.rpc("/base/treeview/load", {
            model: this.model,
            view_id: this.view_id,
            toolbar: this.view_manager ? !!this.view_manager.sidebar : false
        }, this.on_loaded);
    },
    on_loaded: function (data) {
        var self = this;
        this.dataset.read_slice([], 0, false, function (response) {
            self.$element.html(QWeb.render('TreeView', {'field_data':response}));
            id=self.dataset.ids[0];
            self.dataset.domain=[['parent_id','=',parseInt(id,10)]];
            self.dataset.read_slice([], 0, false, function (response) {
                $('#parent_id').change(self.getch(($('#parent_id').attr('value')),0));
                self.$element.append(QWeb.render('TreeView_Secondry', {'child_data':response}));
                $('#child_id').find('div').click(function(){
                    if(jQuery('#child_id').find('#'+(this.id)).find('#subchild').length==0){
                        self.getch(this.id,1);
                    }
                });
            });
        });
    },
    getch: function(id,flag) {

        var self=this;
        if(flag==0){
            $('#parent_id').change(function(){
                self.on_change($('#parent_id').attr('value'),0);
            });
         }
         else if(flag==1){
            self.on_change(id,1);
         }else{
            self.on_change(id,2);
         }
    },
    on_change:function(parentid,flag){
        var self=this;
        if(parentid>0){
            this.dataset.domain=[['parent_id','=',parseInt(parentid,10)]];
            this.dataset.read_slice([],0,false, function (response) {
                if(flag==0){
                    $('#child_id').remove();
                    self.$element.append(QWeb.render('TreeView_Secondry', {'child_data':response}));
                }else if(flag==1){
                    jQuery('#'+parentid).append(QWeb.render('TreeView_Children', {'childdata':response}))
                    $("#subchild").show();
                    jQuery('#'+parentid).find("#parentimg").attr("src", "/base/static/src/img/collapse.gif");
                    $('#'+parentid).find('#subchild').find('#subchild').remove();
                    $('#'+parentid).find('#subchild').slice(1,3).remove();
                }else if(flag==2){
                    $("#subchild #"+parentid).find('#subchild').remove();
                    $("#subchild #"+parentid).find('#childsubchild').remove();
                    jQuery('#subchild #'+parentid).find("#childimg").attr("src", "/base/static/src/img/collapse.gif");
                    $("#subchild #"+parentid).append(QWeb.render('TreeView_SubChildren', {'subchilddata':response}))
                    $("#subchild #"+parentid).find('#childsubchild').show();

                }

	                $('#child_id').find('div').click(function(){
	                   var pathimg=jQuery('#child_id').find('#'+(this.id)).find("#parentimg").attr("src");

                       if(pathimg=='/base/static/src/img/collapse.gif'){
                            jQuery('#child_id').find('#'+(this.id)).find('#parentimg').attr('src','/base/static/src/img/expand.gif');
                            //jQuery('#subchild').find('#'+(this.id)).find('#childsubchild').hide();
                            //jQuery('#child_id').find('#'+(this.id)).find('#subchild').css('display','none');
                       }
                       else if(pathimg=='/base/static/src/img/expand.gif'){
                            if(jQuery('#child_id').find('#'+(this.id)).find('#subchild').length==0){
                                self.getch(this.id,1);
                            }
                       }
	                });

	                $('#child_id div #subchild').find('div').click(function(){
                        if(jQuery('#subchild').find('#'+(this.id)).find('#childsubchild').length==0){
                            self.getch(this.id,2);
                        }else if((jQuery('#subchild').find('#'+(this.id)).find('#childimg').attr('src'))=='/base/static/src/img/collapse.gif'){
                            jQuery('#subchild').find('#'+(this.id)).find('#childimg').attr('src','/base/static/src/img/expand.gif');
                            //jQuery('#subchild').find('#'+(this.id)).find('#childsubchild').hide();
                            jQuery('#subchild').find('#'+(this.id)).find('#childsubchild').css('display','none');
                        }else{
                            jQuery('#subchild').find('#'+(this.id)).find('#childsubchild').css('display','block');
                            //jQuery('#subchild').find('#'+(this.id)).find('#childsubchild').show();
                        }/*else{
                            jQuery('#subchild').find('#'+(this.id)).find('#childimg').attr('src','/base/static/src/img/expand.gif');
                            jQuery('#subchild').find('#'+(this.id)).find('#childsubchild').hide();
                        }*/
	                });
            });
        }
    },
    reload_view: function (grouped) {
        var self = this;
        this.dataset.offset = 0;
        this.dataset.limit = false;
        return this.rpc('/base/treeview/load', {
            model: this.model,
            view_id: this.view_id,
            toolbar: !!this.flags.sidebar
        }, function (field_view_get) {
            self.on_loaded(field_view_get, grouped);
        });
    },
    do_search: function (domains, contexts, groupbys) {
        var self = this;
        return this.rpc('/base/session/eval_domain_and_context', {
            domains: domains,
            contexts: contexts,
            group_by_seq: groupbys
        }, function (results) {
            self.dataset.context = results.context;
            self.dataset.domain = results.domain;
            self.reload_view(!!results.group_by).then(
                $.proxy(self, 'reload_content'));
        });
    }
});
}