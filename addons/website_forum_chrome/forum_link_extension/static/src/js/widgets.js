function odoo_website_forum_chrome_widget(website_forum_chrome) {
    'use strict';
    var QWeb = website_forum_chrome.qweb,
        _t = website_forum_chrome._t;

    website_forum_chrome.website_forum_chrome_widget = openerp.Widget.extend({
        template: "WebsiteForumChrome",
        init: function() {
            this._super.apply(this, arguments);
            this.host = website_forum_chrome.server_parameters.host;
        },
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            $.when(this.check_session()).always(function() {
                self.build_widgets();
                self.screen_selector.set_default_screen();
            });
        },
        check_session: function() {
            var ready = $.Deferred(),
                session = new openerp.Session(undefined, this.host, {use_cors: true});
            session.on('error', this, this.rpc_error);
            session.session_reload().done(function() {
                website_forum_chrome.session = session;
                ready.resolve();
            }).fail(function() {
                ready.reject();
            });
            return ready;
        },
        build_widgets: function() {
            //Creates all widgets instances and add into this object
            /*----------------Screen------------------*/
            this.link_submit_screen = new website_forum_chrome.LinkSubmitScreen(this);
            this.link_submit_screen.appendTo(this.$('.screens'));

            this.link_submit_post_screen = new website_forum_chrome.LinkSubmitPostScreen(this);
            this.link_submit_post_screen.appendTo(this.$('.screens'));

            /*----------------Screen Selector------------------*/
            this.screen_selector = new website_forum_chrome.ScreenSelector({
                screen_set: {
                    'link_submit_screen': this.link_submit_screen,
                    'link_submit_post_screen' : this.link_submit_post_screen
                },
                default_screen: 'link_submit_screen'
            });
        },
        rpc_error: function(error) {
            if (error.data.name === "openerp.http.SessionExpiredException" || error.data.name === "werkzeug.exceptions.Forbidden") {
                this.show_warning({type: "Session Expired", title: "Session Expired", data: { message: _t("Your Odoo session expired. Please refresh the current web page.") }});
                return;
            }
            if (error.code == -32098) {
                this.show_warning({type: "Connection Failed", title: "Connection Failed", data: { message: _t("Connection with Odoo server failed. Please retry after sometime or contact to your administrator.") }});
                return;
            }
            var map_title = {
                user_error: _t('Warning'),
                warning: _t('Warning'),
                access_error: _t('Access Error'),
                missing_error: _t('Missing Record'),
                validation_error: _t('Validation Error'),
                except_orm: _t('Global Business Error'),
                access_denied: _t('Access Denied')
            };
            if (_.has(map_title, error.data.exception_type)) {
                if (error.data.exception_type == 'except_orm' || error.data.exception_type === "except_osv" || error.data.exception_type === "warning" || error.data.exception_type === "access_error") {
                    if (error.data.arguments[1]) {
                        error = _.extend({}, error, {
                            data: _.extend({}, error.data, {
                                message: error.data.arguments[1],
                                title: error.data.arguments[0] !== 'Warning' ? (" - " + error.data.arguments[0]) : ''
                            })
                        });
                    } else {
                        error = _.extend({}, error, {
                            data: _.extend({}, error.data, {
                                message: error.data.arguments[0],
                                title:  ''
                            })
                        });
                    }
                } else {
                    error = _.extend({}, error, {
                        data: _.extend({}, error.data, {
                            message: error.data.arguments[0],
                            title: map_title[error.data.exception_type] !== 'Warning' ? (" - " + map_title[error.data.exception_type]) : ''
                        })
                    });
                }
                this.show_warning(error);
            } else {
                this.show_error(error);
            }
        },
        show_warning: function(error) {
            var self = this;
            this.$dialog_box = $(QWeb.render('Crash.warning', {'error': error})).appendTo("body");
            this.$dialog_box.on('hidden.bs.modal', this, function() {
                self.$dialog_box.modal('hide');
            });
            this.$dialog_box.modal('show');
        },
        show_error: function(error) {
            var self = this;
            this.$dialog_box = $(QWeb.render('Crash.error', {'error': error})).appendTo("body");
            this.$dialog_box.on('hidden.bs.modal', this, function() {
                self.$dialog_box.modal('hide');
            });
            this.$dialog_box.modal('show');
        },
    });

    website_forum_chrome.ScreenSelector = openerp.Class.extend({
        init: function(options) {
            this.screen_set = options.screen_set || {};
            this.default_screen = options.default_screen;
            this.current_screen = null; 
            var screen_name;

            for(screen_name in this.screen_set) {
                this.screen_set[screen_name].hide();
            }
        },
        set_current_screen: function(screen_name, screen_data_set, params, refresh, re_render) {
            var screen = this.screen_set[screen_name];
            if(re_render) {
                screen.renderElement();
            }
            if(!screen) {
                console.error("ERROR: set_current_screen(" + screen_name + ") : screen not found");
            }

            if (refresh || screen !== this.current_screen) {
                if (this.current_screen) {
                    this.current_screen.close();
                    this.current_screen.hide();
                }
                this.current_screen = screen;
                this.current_screen.show();
                if(screen_data_set && this.current_screen.set_screen_values) {
                    this.current_screen.set_screen_values(screen_data_set);
                }
            }
        },
        set_screen_values: function() {
            //void method, child will implement if needed
        },
        set_default_screen: function() {
            this.set_current_screen(this.default_screen);
        },
    });

    website_forum_chrome.ScreenWidget = openerp.Widget.extend({
        //Base widget class, basically meant to show/hide particular screen
        init: function(parent, options) {
            this._super(parent, options);
        },
        show: function() {
            /*
             * this method shows the screen and sets up all the widget related to this screen. Extend this method
             * if you want to alter the behavior of the screen.
             */
            this.hidden = false;
            if (this.$el) {
                this.$el.removeClass('o_hidden');
            }
        },
        close: function() {
            /*
             * this method is called when the screen is closed to make place for a new screen. this is a good place
             * to put your cleanup stuff as it is guaranteed that for each show() there is one and only one close()
             */
        },
        hide: function() {
            /* this methods hides the screen. */
            this.hidden = true;
            if (this.$el) {
                this.$el.addClass('o_hidden');
            }
        },
        renderElement: function() {
            /*
             * we need this because some screens re-render themselves when they are hidden
             * (due to some events, or magic, or both...)  we must make sure they remain hidden.
             * the good solution would probably be to make them not re-render themselves when they are hidden.
             */
            this._super();
            if (this.hidden) {
                if (this.$el) {
                    this.$el.addClass('o_hidden');
                }
            }
        },
    });

    website_forum_chrome.LinkSubmitScreen = website_forum_chrome.ScreenWidget.extend({
        template: 'LinkSubmitScreen',
        events: {
            "click .o_submit_link": "on_submit_link",
            "click .o_login": "on_login",
        },
        init: function(website_forum_chrome_widget) {
            this._super.apply(this, arguments);
            this.website_forum_chrome_widget = website_forum_chrome_widget;
            this.forum_name = website_forum_chrome.server_parameters.forum_name;
            this.host = website_forum_chrome.server_parameters.host;
            this.database = website_forum_chrome.server_parameters.database;
            this.forum_url = _.str.sprintf("%sforum/%s-%s", this.host, this.forum_name.toLowerCase(), website_forum_chrome.server_parameters.forum_id);
            this.can_ask = true;
            this.allow_link = true;
            this.required_karma = 0;
        },
        start: function() {
            var self = this;
            this._super();
            if (this.is_session()) {
                new website_forum_chrome.Model(website_forum_chrome.session, 'forum.forum').call('can_ask', [website_forum_chrome.server_parameters.forum_id])
                    .done(function(result) {
                        self.can_ask = result.can_ask;
                        self.allow_link = result.allow_link;
                        self.required_karma = result.required_karma;
                    });
            }
        },
        is_session: function() {
            //If we having session with same database as config database then directly send call controller with link data
            return website_forum_chrome.session && website_forum_chrome.session.db == website_forum_chrome.server_parameters.database && website_forum_chrome.session.uid;
        },
        on_login: function() {
            var url = _.str.sprintf("%sweb/login?db=%s", this.host, this.database);
            window.open(url);
        },
        on_submit_link: function(e) {
            var self = this;
            var url = _.str.sprintf("/forum_chrome/%s/new?post_type=link", website_forum_chrome.server_parameters.forum_id);
            if (this.is_session()) {
                if (!this.can_ask) {
                    $(e.target).prop('disabled', true);
                    $(e.target).after(QWeb.render('KarmaWarning', {widget: this}));
                    return;
                }
                if (!this.allow_link) {
                    $(e.target).prop('disabled', true);
                    $(e.target).after(_.str.sprintf('<div class="alert alert-warning mt5" role="alert">%s</div>', _t("You can not post links on this forum, \ncontact to your administrator to enable link on this forum.")));
                    return;
                }
                self.get_data().done(function(datas) {
                    return website_forum_chrome.session.rpc(url, datas).done(function(result) {
                        if (result.no_session) {
                            return self.reload_screen();
                        }
                        self.website_forum_chrome_widget.screen_selector.set_current_screen("link_submit_post_screen", {'question_id': result.question_id}, {}, false, true);
                    }).fail(function() {
                        self.reload_screen(); //Maybe call reload_screen in fail only if session is expired
                    });
                });
            } else {
                return self.reload_screen();
            }
        },
        get_data: function() {
            var self = this;
            var def = $.Deferred();
            var result = {'post_type': 'link'};
            this.get_current_uri().done(function(tablink) {
                result = _.extend(result, {'content_link': tablink});
                self.get_current_title().done(function(tabtitle) {
                    result = _.extend(result, {'post_name': tabtitle});
                    def.resolve(result).promise();
                });
            });
            return def;
        },
        get_current_uri: function() {
            var tablink = null;
            var def = $.Deferred();
            chrome.tabs.getSelected(null, function(tab) {
                wait_function(tab.url); //Call wait function so that function need to wait for the value before it is executed
            });
    
            function wait_function(tablink) {
                def.resolve(tablink);
            }
            return def;
        },
        get_current_title: function() {
            var tabtitle = null;
            var def = $.Deferred();
            chrome.tabs.getSelected(null, function(tab) {
                wait_function(tab.title);
            });
    
            function wait_function(title) {
                def.resolve(title);
            }
            return def;
        },
        reload_screen: function() {
            this.website_forum_chrome_widget.screen_selector.set_current_screen("link_submit_screen", {}, {}, true, true);
        },
    });

    website_forum_chrome.LinkSubmitPostScreen = website_forum_chrome.ScreenWidget.extend({
        template: 'LinkSubmitPostScreen',
        events: {
            "click .o_jump_page": "on_jump_page",
            "click .o_cancel": "on_cancel"
        },
        init: function(website_forum_chrome_widget) {
            this._super.apply(this, arguments);
            this.website_forum_chrome_widget = website_forum_chrome_widget;
        },
        start: function() {
            this._super();
        },
        on_jump_page: function() {
            var url = _.str.sprintf("%sforum/%s/question/%s", website_forum_chrome.server_parameters.host, website_forum_chrome.server_parameters.forum_id, this.question_id);
            window.open(url);
        },
        on_cancel: function() {
            this.website_forum_chrome_widget.screen_selector.set_current_screen("link_submit_screen", {}, {}, false, true);
        },
        set_screen_values: function(values) {
            this.question_id = values.question_id;
        },
    });
}