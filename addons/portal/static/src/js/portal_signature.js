odoo.define('portal.signature_form', function (require){
    "use strict";

    require('web_editor.ready');

    var ajax = require('web.ajax');
    var base = require('web_editor.base');
    var core = require('web.core');
    var Widget = require("web.Widget");
    var rpc = require("web.rpc");

    var qweb = core.qweb;

    var SignatureForm = Widget.extend({
        template: 'portal.portal_signature',
        events: {
            'click #o_portal_sign_clear': 'clearSign',
            'click .o_portal_sign_submit': 'submitSign',
            'init #o_portal_sign_accept': 'initSign',
        },

        init: function(parent, options) {
            this._super.apply(this, arguments);
            this.options = _.extend(options || {}, {
                csrf_token: odoo.csrf_token,
            });
        },

        willStart: function() {
            return this._loadTemplates();
        },

        start: function() {
            this.initSign();
        },

        // Signature
        initSign: function () {
            this.$("#o_portal_signature").empty().jSignature({
                'decor-color': '#D1D0CE',
                'color': '#000',
                'background-color': '#fff',
                'height': '142px',
                'width': '100%', // prevent the signature from being too big
            });
            this.empty_sign = this.$("#o_portal_signature").jSignature('getData', 'image');
        },

        clearSign: function () {
            this.$("#o_portal_signature").jSignature('reset');
        },

        submitSign: function (ev) {
            ev.preventDefault();

            // extract data
            var self = this;
            var $confirm_btn = self.$el.find('button[type="submit"]');

            // process : display errors, or submit
            var partner_name = self.$("#o_portal_sign_name").val();
            var signature = self.$("#o_portal_signature").jSignature('getData', 'image');
            var is_empty = signature ? this.empty_sign[1] === signature[1] : true;

            this.$('#o_portal_sign_name').parent().toggleClass('o_has_error', !partner_name).find('.form-control, .custom-select').toggleClass('is-invalid', !partner_name);
            this.$('#o_portal_sign_draw').toggleClass('bg-danger text-white', is_empty);
            if (is_empty || ! partner_name) {
                return false;
            }

            $confirm_btn.prepend('<i class="fa fa-spinner fa-spin"></i> ');
            $confirm_btn.attr('disabled', true);

            return rpc.query({
                route: this.options.callUrl,
                params: {
                    'res_id': this.options.resId,
                    'access_token': this.options.accessToken,
                    'partner_name': partner_name,
                    'signature': signature ? signature[1] : false,
                },
            }).then(function (data) {
                self.$('.fa-spinner').remove();
                if (data.error) {
                    self.$('.o_portal_sign_error_msg').remove();
                    $confirm_btn.before(qweb.render('portal.portal_signature_error', {message: data.error}));
                    $confirm_btn.attr('disabled', false);
                }
                else if (data.success) {
                    $confirm_btn.remove();
                    var $success = qweb.render("portal.portal_signature_success", {widget: data});
                    self.$('#o_portal_sign_draw').parent().replaceWith($success);
                }
                if (data.force_refresh) {
                    if (data.redirect_url) {
                        window.location = data.redirect_url;
                    } else {
                        window.location.reload();
                    }
                }
            });
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @private
         * @returns {Deferred}
         */
        _loadTemplates: function () {
            return ajax.loadXML('/portal/static/src/xml/portal_signature.xml', qweb);
        },
    });

    base.ready().then(function () {
        $('.o_portal_signature_form').each(function () {
            var $elem = $(this);
            var form = new SignatureForm(null, $elem.data());
            form.appendTo($elem);
        });
        // Make the signature responsive when it is displayed in bootstrap modal.
        // More precisely it is too small if this code is not here.
        $('.o_portal_signature_form').parents('.modal').on('shown.bs.modal', function (ev) {
            $('.o_portal_signature_form').trigger('resize');
        });
    });

    return {
        SignatureForm: SignatureForm,
    };
});
