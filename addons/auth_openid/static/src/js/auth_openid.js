
openerp.auth_openid = function(instance) {

var QWeb = instance.web.qweb;
QWeb.add_template('/auth_openid/static/src/xml/auth_openid.xml');

instance.web.Login = instance.web.Login.extend({
    start: function() {
        this._super.apply(this, arguments);
        var self = this;

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

    },


    do_openid_select: function (button, provider, noautosubmit) {
        var self = this;

            self.$openid_selected_button.add(self.$openid_selected_input).removeClass('selected');
            self.$openid_selected_button = self.$element.find(button).addClass('selected');

            var input = _(provider.split(',')).map(function(p) { return 'tr[data-provider="'+p+'"]'; }).join(',');
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

    on_login_invalid: function() {
        var self = this;
        var fragment = jQuery.deparam.fragment();
        if (fragment.loginerror != undefined) {
            this.rpc('/auth_openid/login/status', {}, function(result) {
                if (_.contains(['success', 'failure'], result.status) && result.message) {
                    self.notification.warn('Invalid OpenID Login', result.message);
                }
                if (result.status === 'setup_needed' && result.message) {
                    window.location.replace(result.message);
                }
            });
        }
        return this._super();
    },

    on_submit: function(ev) {

        var dataurl = this.$openid_selected_button.attr('data-url');

        if(!dataurl) {
            // login-password submitted
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
                self.notification.warn(result.title, result.error);
                self.on_login_invalid();
                return;
            }
            if (result.session_id) {
                self.session.session_id = result.session_id;
                self.session.session_save();
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


});


};
