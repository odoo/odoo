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
            self.$element.find('#parent_id').bind('change', function(){
                self.getdata($('#parent_id').val(), 0);
            });
            self.getdata(id);
        });
    },

    // get child data of selected value
    getdata: function (id, flag) {
        var self=this;
        self.dataset.domain = [['parent_id', '=', parseInt(id,10)]];
        self.dataset.read_slice([], 0, false, function (response) {
            if (($('tr #'+id).length) == 1){
                $('tr #'+id).find('td #parentimg').attr('src','/base/static/src/img/collapse.gif');
                $('tr #'+id).after(QWeb.render('TreeView_Secondry', {'child_data':response}));
            }else{
                if (flag == 0){
                    self.$element.find('tr').remove();
                }
                self.$element.append(QWeb.render('TreeView_Secondry', {'child_data':response}));
            }

            $('tr').click(function(){
                divflag=0;
                if ($('#'+(this.id)).length == 1){
                    for (i in response){
                        if (this.id == response[i].id){
                            if (response[i].child_id.length > 0){
                                jQuery(response[i].child_id).each(function(e,chid){
                                    if (jQuery('tr #'+chid).length > 0){
                                        if (jQuery('tr #'+chid).is(':hidden')){
                                            divflag = -1;
                                        }else{
                                            divflag++;
                                        }
                                    }
                                });
                                if (divflag == 0){
                                    if ($('#'+(this.id)).find('td #parentimg').attr('src') == '/base/static/src/img/expand.gif'){
                                        self.getdata(this.id);
                                    }
                                }else if (divflag > 0){
                                    self.showcontent(this.id, 1, response[i].child_id);
                                }else if (divflag == -1){
                                    self.showcontent(this.id, 0, response[i].child_id);
                                }
                            }
                        }
                    }
                }
            });
        });
    },

    // show & hide the contents
    showcontent: function (id, flag, childid) {
        var self=this;
        if (flag == 1){
            $('tr #'+id).find('td #parentimg').attr('src', '/base/static/src/img/expand.gif');
        }
        else{
            $('tr #'+id).find('td #parentimg').attr('src', '/base/static/src/img/collapse.gif');
        }

        for (i in childid){
            if (flag == 1){
                self.dataset.domain = [['parent_id', '=', parseInt(childid[i],10)]];
                self.dataset.read_slice([], 0, false, function (response) {
                    for (j in response){
                        if (jQuery('tr #'+response[j].id).length > 0){
                            jQuery('tr #'+response[j].id).hide();
                        }
                    }
                });
                jQuery ('tr #'+childid[i]).hide();
            }
            else{
                jQuery ('tr #'+childid[i]).show();
            }
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