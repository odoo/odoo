openerp.base.tree = function(openerp) {
openerp.base.views.add('tree', 'openerp.base.TreeView');

/**
 * Genuine tree view (the one displayed as a tree, not the list)
 */
openerp.base.TreeView = openerp.base.View.extend({
    /**
     * Indicates that this view is not searchable, and thus that no search
     * view should be displayed (if there is one active).
     */
    searchable : false,

    init: function(view_manager, session, element_id, dataset, view_id, options) {
        this._super(session, element_id);
        this.view_manager = view_manager || new openerp.base.NullViewManager();
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;
        this.session = session;
        this.columns = [];

        this.options = _.extend({}, this.defaults, options || {});

        this.flags =  this.view_manager.action.flags;

        this.view_manager.flags.search_view = this.view_manager.action.flags.search_view = false;
        this.view_manager.flags.sidebar = this.view_manager.action.flags.sidebar = false;

        this.actionmanager = new openerp.base.ActionManager(this.session, this.element_id);
        this.actionmanager.start();
    },

    start: function () {
        this._super();
        return this.rpc("/base/treeview/load", {
            model: this.model,
            view_id: this.view_id,
            toolbar: this.view_manager ? !!this.view_manager.sidebar : false
        }, this.on_loaded);
    },

    on_loaded: function (fields_view) {
        var self = this;
        this.fields_view = fields_view;
        _(this.fields_view.arch.children).each(function (field) {
            if (field.attrs.modifiers) {
                field.attrs.modifiers = JSON.parse(field.attrs.modifiers);
            }
        });
        this.fields = fields_view.fields;

        this.dataset.read_slice([], 0, false, function (response) {
            self.$element.html(QWeb.render('TreeView', {
                "first_level": response,
                'title': self.fields_view.arch.attrs.string
            }));

            self.$element.find('#parent_id').bind('change', function(){
                self.getdata($('#parent_id').val(), false);
            });
            self.getdata(self.dataset.ids[0], true);
        });
    },

    // get child data of selected value
    getdata: function (id, flag) {

        var self = this;

        self.dataset.domain = [['parent_id', '=', parseInt(id, 10)]];
        self.dataset.read_slice([], 0, false, function (response) {

            var is_padding, row_id, record_id;
            var curr_node = $('tr #treerow_' + id);

            if (curr_node.length == 1) {
                curr_node.find('td:first').children(':first-child').attr('src','/base/static/src/img/collapse.gif');
                curr_node.after(QWeb.render('TreeView.rows', {
                    'records': response,
                    'fields_view' : self.fields_view.arch.children,
                    'field' : self.fields
                }));


                for (var i = 0; i < response.length; i++) {
                    row_id = $('tr #treerow_' + response[i].id);

                    if (row_id && row_id.find('td:first').children(':first-child').attr('id') == 'parentimg_' + response[i].id) {
                        row_id.find('td:first').append('<span>'+row_id.find('td:eq(1)').text()+'</span>');
                        row_id.find('td:eq(1)').remove();
                        is_padding = true;
                    }
                }

                var padding = curr_node.find('td').css('paddingLeft');
                var padd = parseInt(padding.replace('px',''), 10);
                var fixpadding;

                for (var i = 0; i < response.length; i++) {
                    row_id = $('tr #treerow_' + response[i].id);
                    if (row_id) {
                        if (!is_padding) {
                            fixpadding = padd + 40;
                            row_id.find('td:first').css('paddingLeft', fixpadding);
                        } else {
                            if (padd == 1) {
                                fixpadding = padd + 17;
                            } else {
                                fixpadding = padd + 20;
                            }
                            var curr_node_elem = row_id.find('td:first');
                            curr_node_elem.children(':first-child').addClass("parent_top");
                            if (curr_node_elem.children(':first-child').attr('id') == "parentimg_" + response[i].id) {
                                curr_node_elem.css('paddingLeft', fixpadding );
                            } else {
                                curr_node_elem.css('paddingLeft', (fixpadding + 20));
                            }
                        }
                    }
                }
            } else {
                if (!flag) {
                    self.$element.find('table').remove();
                }
                self.$element.append(QWeb.render('TreeView.architecture', {
                    'records': response,
                    'fields_view': self.fields_view.arch.children,
                    'fields': self.fields
                }));

                self.$element.find('tr[id ^= treerow_]').each( function() {
                    if ($(this).find('td:first').children(':first-child').attr('id')) {
                        $(this).find('td:first').append('<span>' + $(this).find('td:eq(1)').text() + '</span>');
                        $(this).find('td:eq(1)').remove();
                    }
                    $(this).find('td').children(':first-child').addClass("parent_top");
                    if (!($(this).find('td').children(':first-child').attr('id'))) {
                        $(this).find('td:first').css('paddingLeft', '20px');
                    }
                });
            }

            self.$element.find('tbody tr').find('td:first').mouseover( function() {
                $(this).addClass('mouse-over');
            }).mouseout( function() {
                $(this).removeClass('mouse-over');
            });

            self.$element.find('tr[id ^= treerow_] td').children(':first-child').click( function() {
                var is_loaded = 0;
                if ($(this).length == 1) {
                    record_id = (this.id).split('_')[1];
                    for (var i = 0; i < response.length; i++) {
                        if (record_id == response[i].id && response[i].child_id.length > 0) {
                            $(response[i].child_id).each (function(e, childid) {
                                if ($('tr #treerow_' + childid).length > 0) {
                                    if ($('tr #treerow_' + childid).is(':hidden')) {
                                        is_loaded = -1;
                                    } else {
                                        is_loaded++;
                                    }
                                }
                            });
                            if (is_loaded == 0) {
                                if ($(this).attr('src') == '/base/static/src/img/expand.gif') {
                                    self.getdata(record_id, true);
                                }
                            } else if (is_loaded > 0) {
                                self.showcontent(record_id, true, response[i].child_id);
                            } else {
                                self.showcontent(record_id, false, response[i].child_id);
                            }
                        }
                    }
                }
            });

            self.$element.find('tr[id ^= treerow_]').find('td').children(':last-child').click( function(e) {
                row_id = $(this).parent().parent().attr('id');
                record_id = row_id.split('_')[1];
                self.showrecord(record_id, self.model);
                e.stopImmediatePropagation();
            });
        });
    },

    // Get details in listview
    showrecord: function(id, model){
        var self = this;
        self.dataset.model = 'product.product';
        self.dataset.domain = [['categ_id', 'child_of', parseInt(id, 10)]];
        var modes = !!modes ? modes.split(",") : ["tree", "form"];
        var views = [];
        _.each(modes, function(mode) {
            var view = [false, mode == "tree" ? "list" : mode];
            if (self.fields.views && self.fields.views[mode]) {
                view.push(self.fields.views[mode]);
            }
            views.push(view);
        });
        this.actionmanager.do_action({
            "res_model" : self.dataset.model,
            "domain" : self.dataset.domain,
            "views" : views,
            "type" : "ir.actions.act_window",
            "auto_search" : true,
            "view_mode" : "list",
            "flags": {
                search_view: true,
                sidebar : true,
                views_switcher : true,
                action_buttons : true,
                pager: true,
                new_window : true
            }
        });

        self.dataset.model = model;
    },

    // show & hide the contents
    showcontent: function (id, flag, childid) {
        var self = this;

        var first_child = $('tr #treerow_' + id).find('td').children(':first-child');
        if (flag) {
            first_child.attr('src', '/base/static/src/img/expand.gif');
        }
        else {
            first_child.attr('src', '/base/static/src/img/collapse.gif');
        }

        for (var i = 0; i < childid.length; i++) {
            if (flag) {
                self.dataset.domain = [['parent_id', '=', parseInt(childid[i], 10)]];
                var childimg = $('tr #treerow_' + childid[i]).find('td').children(':first-child').attr('src');

                if (childimg == "/base/static/src/img/collapse.gif") {
                    $('tr #treerow_' + childid[i]).find('td').children(':first-child').attr('src','/base/static/src/img/expand.gif');
                }

                self.dataset.read_slice([], 0, false, function (response) {
                    for (var j = 0; j < response.length; j++) {
                        var res_ids = $('tr #treerow_' + response[j].id);
                        if (res_ids.length > 0) {
                            res_ids.hide();
                            var subchildids = response[j].child_id;
                            if (subchildids.length > 0) {
                                self.showcontent(response[j].id, true, subchildids);
                            }
                        }
                    }
                });
                $ ('tr #treerow_' + childid[i]).hide();
            }
            else {
                $ ('tr #treerow_' + childid[i]).show();
            }
        }
    },

    do_show: function () {
        this.$element.show();
        this.view_manager.sidebar.do_refresh(true);
    },

    do_hide: function () {
        this.$element.hide();
        this.hidden = true;
    }
});
};
