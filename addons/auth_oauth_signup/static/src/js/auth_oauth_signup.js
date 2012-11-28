openerp.auth_oauth_signup = function(instance) {

    // override Login._oauth_state to add the signup token in the state
    instance.web.Login.include({
        _oauth_state: function(provider) {
            var state = this._super.apply(this, arguments);
            if (this.params.token) {
                state.t = this.params.token;
            }
            return state;
        },
    });

};
