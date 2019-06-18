odoo.define('website_profile.website_profile', function (require) {
'use strict';

var sAnimations = require('website.content.snippets.animation');
var Wysiwyg = require('web_editor.wysiwyg.root');

//TODO DBE : to change into publicWidget = require('web.public.widget'); after forward port in master
sAnimations.registry.websiteProfile = sAnimations.Class.extend({
    selector: '.o_wprofile_email_validation_container',
    read_events: {
        'click .send_validation_email': '_onSendValidationEmailClick',
        'click .validated_email_close': '_onCloseValidatedEmailClick',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    /**
     * @private
     * @param {Event} ev
     */
    _onSendValidationEmailClick: function (ev) {
        ev.preventDefault();
        var self = this;
        var $element = $(ev.currentTarget);
        this._rpc({
            route: '/profile/send_validation_email',
            params: {'redirect_url': $element.data('redirect_url')},
        }).then(function (data) {
            if (data) {
                self.$('button.validation_email_close').click();
            }
        });
    },

    /**
     * @private
     */
    _onCloseValidatedEmailClick: function () {
        this._rpc({
            route: '/profile/validate_email/close',
        });
    },
});

sAnimations.registry.websiteProfileEditor = sAnimations.Class.extend({
    selector: '.o_wprofile_editor_form',
    read_events: {
        'click .o_wprofile_submit_btn': '_onSubmitClick',
    },

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        if (this.editableMode) {
            return def;
        }
        var $textarea = this.$('textarea.load_editor');
        var wysiwyg = new Wysiwyg(this, {
            recordInfo: {
                context: this._getContext(),
                res_model: 'res.users',
                res_id: parseInt(this.$('input[name=user_id]').val()),
            },
        });

        if (!$textarea.val().match(/\S/)) {
            $textarea.val('<p><br/></p>');
        }
        return $.when(def, wysiwyg.attachTo($textarea));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onSubmitClick: function () {
        this.$('textarea.load_editor').data('wysiwyg').save();
    },
});

return sAnimations.registry.websiteProfile;

});
