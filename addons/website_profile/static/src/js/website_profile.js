odoo.define('website_profile.website_profile', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var wysiwygLoader = require('web_editor.loader');
const rpc = require('web.rpc');

publicWidget.registry.websiteProfile = publicWidget.Widget.extend({
    selector: '.o_wprofile_email_validation_container',
    read_events: {
        'click .send_validation_email': 'async _onSendValidationEmailClick',
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
        var $element = $(ev.currentTarget);
        return this._rpc({
            route: '/profile/send_validation_email',
            params: {'redirect_url': $element.data('redirect_url')},
        }).then(function (data) {
            if (data) {
                window.location = $element.data('redirect_url');
                return new Promise(() => {});
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

publicWidget.registry.websiteProfileEditor = publicWidget.Widget.extend({
    selector: '.o_wprofile_editor_form',
    read_events: {
        'click .o_forum_profile_pic_edit': '_onEditProfilePicClick',
        'change .o_forum_file_upload': '_onFileUploadChange',
        'click .o_forum_profile_pic_clear': '_onProfilePicClearClick',
    },

    /**
     * @override
     */
    start: async function () {
        var def = this._super.apply(this, arguments);
        if (this.editableMode) {
            return def;
        }

        var $textarea = this.$('textarea.o_wysiwyg_loader');

        const resId = parseInt(this.$('input[name=user_id]').val());
        const recordContent = await rpc.query({
            model: 'res.users',
            method: 'get_website_description',
            args: [[resId]],
        }) || '';

        this._wysiwyg = await wysiwygLoader.loadFromTextarea(this, $textarea[0], {
            recordInfo: {
                context: this._getContext(),
                res_model: 'res.users',
                res_id: resId,

            },
            value: recordContent,
            resizable: true,
            userGeneratedContent: true,
        });

        return Promise.all([def]);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onEditProfilePicClick: function (ev) {
        ev.preventDefault();
        $(ev.currentTarget).closest('form').find('.o_forum_file_upload').trigger('click');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onFileUploadChange: function (ev) {
        if (!ev.currentTarget.files.length) {
            return;
        }
        var $form = $(ev.currentTarget).closest('form');
        var reader = new window.FileReader();
        reader.readAsDataURL(ev.currentTarget.files[0]);
        reader.onload = function (ev) {
            $form.find('.o_forum_avatar_img').attr('src', ev.target.result);
        };
        $form.find('#forum_clear_image').remove();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onProfilePicClearClick: function (ev) {
        var $form = $(ev.currentTarget).closest('form');
        $form.find('.o_forum_avatar_img').attr('src', '/web/static/img/placeholder.png');
        $form.append($('<input/>', {
            name: 'clear_image',
            id: 'forum_clear_image',
            type: 'hidden',
        }));
    },
});

return publicWidget.registry.websiteProfile;

});
