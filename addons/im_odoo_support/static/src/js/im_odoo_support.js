(function(){

    "use strict";

    var _t = openerp._t;
    openerp.im_odoo_support = {};
    var COOKIE_NAME = 'livechat_conversation';
    var SERVICE_URL = 'https://services.odoo.com/';

    openerp.im_odoo_support.OdooSupport = openerp.Widget.extend({
        init: function(login, uuid, params, options){
            var self = this;
            this._super();
            this.login = login;
            this.uuid = uuid;

            this.options = _.extend(options || {}, {'defaultUsername' : login});
            this.params = _.extend(params || {}, {'database_uuid' : uuid});

            this.assets_loaded = false;
            this.session = false;
            // bind event
            $(window).on("odoo_support_ready_to_bind", this, _.bind(this.bind_actions, this));
        },
        bind_actions: function(event, button){
            if(button === 'usermenu'){
                openerp.client.$('.oe_user_menu_placeholder .odoo_support_contact').on('click', this, _.bind(this.click_action, this));
                // check auto start if cookie
                var session = openerp.get_cookie(COOKIE_NAME);
                if(session){
                    this.start_support();
                }
            }
            if(button === 'im_contact'){
                if(openerp.im_chat && openerp.im_chat.single){
                    openerp.im_chat.single.$('.odoo_support_contact').on('click',this, _.bind(this.click_action, this));
                }
            }
        },
        click_action: function(){
            var session = openerp.get_cookie(COOKIE_NAME);
            if(!session){
                this.start_support();
            }
        },
        start_support: function(){
            var self = this;
            if(!this.assets_loaded){
                this.load_assets().then(function(){
                    try{
                        odoo_support.im_livechat.support = new odoo_support.im_livechat.LiveSupport(self.options, self.params);
                        // bind event change status
                        odoo_support.im_livechat.support.on('im_odoo_support_status', this, function(is_online){
                            if(openerp.im_chat && openerp.im_chat.single){
                                openerp.im_chat.single.support_user.$(".oe_im_user_online").toggle(is_online);
                            }
                        });
                    }catch(e){
                        self.error_on_start(e);
                    }
                }).fail(function(e){
                   self.error_on_start(e);
                });
            }else{
                odoo_support.im_livechat.support.start();
            }
        },
        error_on_start: function(e){
            self.assets_loaded = false;
            openerp.client.do_warn(_t("Error"), _t("The connection with the Odoo Support Server failed. Please retry in a few minutes, or send an email to support@odoo.com ."));
        },
        load_assets: function(){
            var self = this;
            var add_asset = function(file_url, type) {
                var def = $.Deferred();
                if(type === 'js'){
                    $.getScript( file_url, function( data, textStatus, jqxhr ) {
                        def.resolve();
                    }).fail(function(){
                        def.reject();
                    });
                    return def;
                }else{
                    $('<link rel="stylesheet" href="' + file_url + '"></link>').appendTo($("head")).ready(function() {
                        def.resolve();
                    });
                    return def;
                }
            };
            var defs = [];
            defs.push(add_asset(SERVICE_URL+"odoo-livechat/assets/js", 'js'));
            defs.push(add_asset(SERVICE_URL+"odoo-livechat/assets/css", 'css'));
            return $.when.apply($, defs).then(function(res){
                self.assets_loaded = true;
                return res;
            }, function(){
                self.error_on_start();
            });
        },
    });

    // display support contact button (in chat user list, if installed) and in dropdown user menu.
    if(openerp.im_chat){
        openerp.im_chat.InstantMessaging.include({
            start: function(){
                this._super.apply(this, arguments);
                var user = {
                    "id" : -1,
                    "name": _t('Odoo Support'),
                    "im_status": 'online',
                    "image_url": "/im_odoo_support/static/img/odoo_o_small.png"
                };
                var widget = new openerp.im_chat.UserWidget(self, user);
                widget.prependTo(self.$(".oe_im_users"));
                widget.$el.addClass('odoo_support_contact');
                this.support_user = widget;

                $(window).trigger('odoo_support_ready_to_bind','im_contact');
            },
            search_users_status: function(e){
                var self = this;
                this._super.apply(this, arguments).then(function(res){
                    if(self.$('.oe_im_searchbox').val().length === 0 || _t("Odoo Support").toLowerCase().indexOf(self.$('.oe_im_searchbox').val().toLowerCase()) != -1){
                        self.support_user.$el.show();
                    }else{
                        self.support_user.$el.hide();
                    }
                    return res;
                });
            }
        });
    }

    openerp.web.UserMenu.include({
        do_update: function(){
            $(window).trigger('odoo_support_ready_to_bind', 'usermenu');
            return this._super.apply(this, arguments);
        },
    });

})();
