
openerp.auth_openid = function(instance) {

var QWeb = instance.web.qweb;

instance.web.Login = instance.web.Login.extend({
    start: function() {
        this._super.apply(this, arguments);
        var self = this;

        this._default_error_message = this.$element.find('.oe_login_error_message').text();

        this.$openid_selected_button = $();
        this.$openid_selected_input = $();
        this.$openid_selected_provider = null;


        var openIdProvider = null;
        if (this.has_local_storage && this.remember_credentials) {
            openIdProvider = localStorage.getItem('openid-provider');
        }

        if (openIdProvider) {
            $openid_selected_provider = openIdProvider;
            this.do_openid_select('a[href="#' + openIdProvider + '"]', openIdProvider, true);

            if (this.has_local_storage && this.remember_credentials) {
                this.$openid_selected_input.find('input').val(localStorage.getItem('openid-login'));
            }
        }
        else {
            this.do_openid_select('a[data-url=""]', 'login,password', true);
        }

        this.$element.find('a[data-url]').click(function (event) {
            event.preventDefault();
            var selected_oidh = $(this).attr('href').substr(1);
            if (selected_oidh != self.$openid_selected_provider) {
                self.do_openid_select(this, selected_oidh);
            }
        });

        this._check_error();
    },


    do_openid_select: function (button, provider, noautosubmit) {
        var self = this;

            self.$openid_selected_button.add(self.$openid_selected_input).removeClass('selected');
            self.$openid_selected_button = self.$element.find(button).addClass('selected');

            var input = _(provider.split(',')).map(function(p) { return 'li[data-provider="'+p+'"]'; }).join(',');
            self.$openid_selected_input = self.$element.find(input).addClass('selected');

            self.$openid_selected_input.find('input:first').focus();
            self.$openid_selected_provider = (self.$openid_selected_button.attr('href') || '').substr(1);

            if (self.has_local_storage && self.remember_credentials) {
                localStorage.setItem('openid-provider', self.$openid_selected_provider);
            }

            if (!noautosubmit && self.$openid_selected_input.length == 0) {
                self.$element.find('form').submit();
            }

    },

    _check_error: function() {
        var self = this;
        if (this.params.loginerror !== undefined) {
            this.rpc('/auth_openid/login/status', {}, function(result) {
                if (_.contains(['success', 'failure'], result.status) && result.message) {
                    self.do_warn('Invalid OpenID Login', result.message);
                }
                if (result.status === 'setup_needed' && result.message) {
                    window.location.replace(result.message);
                }
            });
        }
    },

    on_submit: function(ev) {

        var dataurl = this.$openid_selected_button.attr('data-url');

        if(!dataurl) {
            // login-password submitted
            this.reset_error_message();
            this._super(ev);
        } else {
            ev.preventDefault();

            var id = this.$openid_selected_input.find('input').val();
            if (this.has_local_storage && this.remember_credentials) {
                localStorage.setItem('openid-login', id);
            }

            var db = this.$element.find("form [name=db]").val();
            var openid_url = dataurl.replace('{id}', id);

            this.do_openid_login(db, openid_url);

        }
    },

    do_openid_login: function(db, openid_url) {
        var self = this;
        this.rpc('/auth_openid/login/verify', {'db': db, 'url': openid_url}, function(result) {
            if (result.error) {
                self.do_warn(result.title, result.error);
                return;
            }
            if (result.session_id) {
                self.session.set_cookie('session_id', result.session_id);
            }
            if (result.action === 'post') {
                document.open();
                document.write(result.value);
                document.close();
            } else if (result.action === 'redirect') {
                window.location.replace(result.value);
            } else {
                // XXX display error ?
            }

        });
    },

    do_warn: function(title, msg) {
        //console.warn(title, msg);
        this.$element.find('.oe_login_error_message').text(msg).show();
        this._super(title, msg);
    },

    reset_error_message: function() {
        this.$element.find('.oe_login_error_message').text(this._default_error_message);
    }

});


};
