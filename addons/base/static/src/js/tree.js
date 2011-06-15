openerp.base.tree = function(openerp) {
openerp.base.views.add('tree', 'openerp.base.TreeView');

/**
 * Genuine tree view (the one displayed as a tree, not the list)
 */
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
            self.$element.html(QWeb.render('TreeView', {'field_data' : response}));
            id=self.dataset.ids[0];
            self.$element.find('#parent_id').bind('change', function(){
                self.getdata($('#parent_id').val(), 0);
            });
            self.getdata(id);
        });
    },

    // get child data of selected value
    getdata: function (id, flag) {
        var self = this;
        var paddingflag = 0;
        self.dataset.domain = [['parent_id', '=', parseInt(id, 10)]];
        self.dataset.read_slice([], 0, false, function (response) {
            if (($('tr #treerow_' + id).length) == 1) {
                $('tr #treerow_' + id).find('td #parentimg').attr('src','/base/static/src/img/collapse.gif');
                $('tr #treerow_' + id).after(QWeb.render('TreeView_Secondry', {'child_data' : response}));
                parentlen = $('tr #treerow_' + id).find('td').length;
                for (i in response) {
                    if ($('tr #treerow_' + response[i].id)) {
                        childlen = $('tr #treerow_' + response[i].id).find('td').length;
                        while (childlen < (parentlen + 1)) {
                            $('tr #treerow_' + response[i].id).find('td:eq(0)').before('<td></td>');
                            childlen++;
                        }
                    }
                }
                for (i in response) {
                    if ($('tr #treerow_' + response[i].id)) {
                        childlen = $('tr #treerow_' + response[i].id).find('td').length;
                        if ($('tr #treerow_' + response[i].id).find('td:eq('+ (childlen - 2) +')').find('#parentimg').length > 0){
                            paddingflag=1;
                        }
                    }
                }

                tdlen = $('tr #treerow_' + id).find('td').length;
                paddingno = $('tr #treerow_' + id).find('td:eq('+ (tdlen - 1) +')').css('paddingLeft');
                padd = paddingno.split('px');
                for (i in response) {
                    if ($('tr #treerow_' + response[i].id)) {
                        childlen = $('tr #treerow_' + response[i].id).find('td').length;
                        textoftd = $('tr #treerow_' + response[i].id).find('td:eq('+ (childlen - 1) +')').text();
                        if (paddingflag == 0) {
                            if (parseInt(padd[0], 10) == 1) {
                                fix = (parseInt(padd[0], 10) + 20);
                            } else {
                                fix = (parseInt(padd[0], 10) + 40);
                            }
                            $('tr #treerow_' + response[i].id).find('td:eq('+ (childlen - 2) +')').css({ paddingLeft : fix });

                        } else {
                            if (parseInt(padd[0], 10) == 1) {
                                fix = (parseInt(padd[0],10) + 2);
                            } else {
                                fix = (parseInt(padd[0], 10) + 20);
                            }
                            if ($('tr #treerow_' + response[i].id).find('td:eq('+ (childlen - 2) +')').find('#parentimg').length == 0) {
                                $('tr #treerow_' + response[i].id).find('td:eq('+ (childlen - 2) +')').css({ paddingLeft : (fix+20) });
                            }else{
                                $('tr #treerow_' + response[i].id).find('td:eq('+ (childlen - 2) +')').find('#parentimg').addClass("parent_top");
                                $('tr #treerow_' + response[i].id).find('td:eq('+ (childlen - 2) +')').css({ paddingLeft : fix });
                            }
                        }
                        $('tr #treerow_' + response[i].id).find('td:eq('+ (childlen - 2) +')').attr('colspan', '2');
                        $('tr #treerow_' + response[i].id).find('td:eq('+ (childlen - 2) +')').append(textoftd);
                        $('tr #treerow_' + response[i].id).find('td:eq('+ (childlen - 1) +')').remove();
                    }
                }
            } else {
                if (flag == 0) {
                    self.$element.find('tr').remove();
                }
                self.$element.append(QWeb.render('TreeView_Secondry', {'child_data': response}));
            }

            self.$element.find('tr').mouseover( function() {
                $(this).css({ color : '#0000FF' });
            });
            self.$element.find('tr').mouseout( function() {
                $(this).css({ color : '#000000' });
            });

            $('tr').click(function() {
                divflag=0;
                if ($('#'+(this.id)).length == 1) {
                    rowid = (this.id).split('_');

                    for (i in response) {
                        if (rowid[1] == response[i].id){
                            if (response[i].child_id.length > 0) {
                                jQuery(response[i].child_id).each (function(e, chid) {
                                    if (jQuery('tr #treerow_' + chid).length > 0) {
                                        if (jQuery('tr #treerow_' + chid).is(':hidden')) {
                                            divflag = -1;
                                        } else {
                                            divflag++;
                                        }
                                    }
                                });
                                if (divflag == 0) {
                                    if ($('#' + (this.id)).find('td #parentimg').attr('src') == '/base/static/src/img/expand.gif') {
                                        self.getdata(rowid[1]);
                                    }
                                } else if (divflag > 0) {
                                    self.showcontent(rowid[1], 1, response[i].child_id);
                                } else if (divflag == -1) {
                                    self.showcontent(rowid[1], 0, response[i].child_id);
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
        var self = this;
        var subchildids = "";
        if (flag == 1) {
            $('tr #treerow_' + id).find('td #parentimg').attr('src', '/base/static/src/img/expand.gif');
        }
        else {
            $('tr #treerow_' + id).find('td #parentimg').attr('src', '/base/static/src/img/collapse.gif');
        }

        for (i in childid) {
            if (flag == 1) {
                self.dataset.domain = [['parent_id', '=', parseInt(childid[i], 10)]];
                childimg = $('tr #treerow_' + childid[i]).find('td').find('#parentimg').attr('src');

                if (childimg == "/base/static/src/img/collapse.gif") {
                    $('tr #treerow_' + childid[i]).find('td').find('#parentimg').attr('src','/base/static/src/img/expand.gif');
                }

                self.dataset.read_slice([], 0, false, function (response) {
                    for (j in response) {
                        if (jQuery('tr #treerow_' + response[j].id).length > 0) {
                            jQuery('tr #treerow_' + response[j].id).hide();
                            subchildids = response[j].child_id;
                            if (subchildids.length > 0) {
                                self.showcontent(response[j].id, 1, subchildids);
                            }
                        }
                    }

                });
                jQuery ('tr #treerow_' + childid[i]).hide();
            }
            else {
                jQuery ('tr #treerow_' + childid[i]).show();
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