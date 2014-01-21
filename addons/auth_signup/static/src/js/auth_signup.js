openerp.auth_signup = function(instance) {
    openerp.web.LoginForm.include({
        start: function () {
            var self = this;
            this.$el.on('submit', function () {
                var password = self.get_password_field('password');
                var confirm_password = self.get_password_field('confirm_password');
                if (password && confirm_password && (password.value != confirm_password.value)) {
                    alert("Passwords do not match; please retype them.");
                    return false;
                }
            });
        },
        get_password_field: function (field) {
            var selector = 'input[name="' + field + '"][type="password"]:visible';
            return this.$(selector)[0];
        },
    });
};
