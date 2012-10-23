openerp.auth_reset_password = function(instance) {
    var _t = instance.web._t;

    instance.web.Login.include({
        start: function() {
            this.$('a.oe_reset_password').click(this.do_reset_password);
            return this._super();
        },
        do_reset_password: function(ev) {
            if (ev) {
                ev.preventDefault();
            }
            var db = this.$("form [name=db]").val();
            var login = this.$("form input[name=login]").val();
            if (!db) {
                this.do_warn("Login", "No database selected !");
                return false;
            } else if (!login) {
                this.do_warn("Login", "Please enter a username or email address.")
                return false;
            }
            var params = {
                dbname : db,
                login: login,
            };
            var url = "/auth_reset_password/reset_password?" + $.param(params);
            window.location = url;
        }
    });
};
