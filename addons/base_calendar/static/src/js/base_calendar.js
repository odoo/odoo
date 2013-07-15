openerp.base_calendar = function(instance) {
var _t = instance.web._t;
var QWeb = instance.web.qweb;
instance.base_calendar = {}

    instance.base_calendar.invite = instance.web.Widget.extend({

        init: function(parent,db,token,action,view_type,id,status) {
            this._super();
            this.db = db;
            this.token = token;
            this.status = status;
            this.action = action;
            this.view_type = view_type;
            this.id = id;
        },
        start: function() {
            var self = this;
            if (instance.session.session_is_valid(self.db)) {
                self.show_meeting();
            } else {
                self.show_login()
            }
        },
        show_login: function(action) {
            var self =  this;
            this.destroy_content();
            this.login = new instance.web.Login_extended(this,self.action);
            this.login.appendTo(this.$el);
            this.login.on('db_loaded',self,function(db,login){
                if (instance.session.session_is_valid(db)) {
                    (self.show_meeting()).done(function(){
                        self.login.off('db_loaded');
                    });
                }
                else{
                    self.show_login();
                }
            })
        },
        destroy_content: function() {
            _.each(_.clone(this.getChildren()), function(el) {
                el.destroy();
            });
            this.$el.children().remove();
        },
        show_meeting : function(){
            var db = this.db;
            var att_status = "do_decline";
            var self = this;
            var reload_page = function(){
                return location.replace(_.str.sprintf('/?db=%s#view_type=%s&model=crm.meeting&action=%s&active_id=%s',self.db,self.view_type,self.action,self.id));
            }
            if(self.status === 'accepted'){att_status = "do_accept";}
            var calender_attendee = new instance.web.Model('calendar.attendee')
            var check = calender_attendee.query(["state"]).filter([["id", "=", parseInt(this.token)]]).first();
            return check.done(function(res){
                if(res['state'] === "needs-action"){
                    return calender_attendee.call(att_status,[[parseInt(self.token)]]).done(reload_page);
                }
                reload_page();
            });
        },
    });
    instance.web.Login_extended = instance.web.Login.extend({
        do_login: function (db, login, password) {
            var self = this;
            (this._super.apply(this,arguments)).done(function(){
               self.trigger('db_loaded',db,login)
            });
        }
    });
    instance.web.form.Many2Many_invite = instance.web.form.FieldMany2ManyTags.extend({
        initialize_content: function() {
            var self = this;
            var ignore_blur = false;
            self.$text = this.$("textarea");
            if (this.get("effective_readonly"))
                return;
            self.$text.textext({
                plugins : 'tags arrow autocomplete',
                html: {
                    tag: '<div class="text-tag"><div class="text-button"><a class="oe_invitation custom-edit"/><span class="text-label"/><a class="text-remove"/></div></div>'
                },
                autocomplete: {
                    render: function(suggestion) {
                        return $('<span class="text-label"/>').
                                 data('index', suggestion['index']).html(suggestion['label']);
                    }
                },
                ext: {
                    autocomplete: {
                        selectFromDropdown: function() {
                            this.trigger('hideDropdown');
                            var index = Number(this.selectedSuggestionElement().children().children().data('index'));
                            var data = self.search_result[index];
                            if (data.id) {
                                self.add_id(data.id);
                            } else {
                                ignore_blur = true;
                                data.action();
                            }
                            this.trigger('setSuggestions', {result : []});
                        },
                    },
                    tags: {
                        isTagAllowed: function(tag) {
                            return !!tag.name;

                        },
                        removeTag: function(tag) {
                            var id = tag.data("id");
                            self.set({"value": _.without(self.get("value"), id)});
                        },
                        renderTag: function(stuff) {
                            return $.fn.textext.TextExtTags.prototype.renderTag.
                                call(this, stuff).data("id", stuff.id);
                        },
                    },
                    itemManager: {
                        itemToString: function(item) {
                            return item.name;
                        },
                    },
                    core: {
                        onSetInputData: function(e, data) {
                            if (data == '') {
                                this._plugins.autocomplete._suggestions = null;
                            }
                            this.input().val(data);
                        },
                    },
                },
            }).bind('getSuggestions', function(e, data) {
                var _this = this;
                var str = !!data ? data.query || '' : '';
                self.get_search_result(str).done(function(result) {
                    self.search_result = result;
                    $(_this).trigger('setSuggestions', {result : _.map(result, function(el, i) {
                        return _.extend(el, {index:i});
                    })});
                });
            }).bind('hideDropdown', function() {
                self._drop_shown = false;
            }).bind('showDropdown', function() {
                self._drop_shown = true;
            });
            self.tags = self.$text.textext()[0].tags();
            self.$text
                .focusin(function () {
                    self.trigger('focused');
                    ignore_blur = false;
                })
                .focusout(function() {
                    self.$text.trigger("setInputData", "");
                    if (!ignore_blur) {
                        self.trigger('blurred');
                    }
                }).keydown(function(e) {
                    if (e.which === $.ui.keyCode.TAB && self._drop_shown) {
                        self.$text.textext()[0].autocomplete().selectFromDropdown();
                    }
                });
        },
        render_value: function() {
            var self = this;
            var dataset = new instance.web.DataSetStatic(this, this.field.relation, self.build_context());
            var values = self.get("value");
            var handle_names = function(data) {
                if (self.isDestroyed())
                    return;
                if (! self.get("effective_readonly")) {
                    self.tags.containerElement().children().remove();
                    self.$('textarea').css("padding-left", "3px");
                    self.tags.addTags(_.map(data, function(el) {return {name: el[1], id:el[0]};}));
                    var tag_element = self.tags.tagElements();
                    _.each(data,function(value, key){
                        $(tag_element[key]).find(".custom-edit").addClass(data[key][2])
                    })
                } else {
                    self.$el.html(QWeb.render("Many2Many_invite", {elements: data}));
                }
            };
            if (! values || values.length > 0) {
                if(self.getParent().datarecord.attendee_ids && self.getParent().datarecord.attendee_ids.length == values.length){
                    return new instance.web.Model("calendar.attendee").call('read',[self.getParent().datarecord.attendee_ids ,['state','cn','partner_id']]).then(function(res){
                        data = []
                        _.each(res,function(val){
                            data.push([val['partner_id'][0],val['cn'],val['state']])
                        });
                        handle_names(data)
                    });
                } else {
                    this._display_orderer.add(dataset.name_get(values)).done(handle_names); }
            } else { handle_names([]); }
        },

    });
    instance.web.form.widgets = instance.web.form.widgets.extend({
        'Many2Many_invite' : 'instance.web.form.Many2Many_invite',
    });
    instance.base_calendar.event = function (db, token, action, view_type, id, status) {
        instance.session.session_bind(instance.session.origin).done(function () {
            new instance.base_calendar.invite(null,db,token,action,view_type,id,status).appendTo($("body").addClass('openerp'));
        });
    }
};
//vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
