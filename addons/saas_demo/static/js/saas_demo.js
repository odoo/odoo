openerp.saas_demo = function (instance) {

instance.web.WebClient.include({
    check_timezone: function() {
        // Disable timezone check for saas demo
    },
});

};
