/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { loadWysiwygFromTextarea } from "@web_editor/js/frontend/loadWysiwygFromTextarea";

publicWidget.registry.websiteProfile = publicWidget.Widget.extend({
    selector: '.o_wprofile_email_validation_container',
    read_events: {
        'click .send_validation_email': '_onSendValidationEmailClick',
        'click .validated_email_close': '_onCloseValidatedEmailClick',
    },

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
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
        this.rpc('/profile/send_validation_email', {
            'redirect_url': $element.data('redirect_url'),
        }).then(function (data) {
            if (data) {
                window.location = $element.data('redirect_url');
            }
        });
    },

    /**
     * @private
     */
    _onCloseValidatedEmailClick: function () {
        this.rpc('/profile/validate_email/close');
    },
});

publicWidget.registry.websiteProfileEditor = publicWidget.Widget.extend({
    selector: '.o_wprofile_editor_form',
    read_events: {
        'click .o_forum_profile_pic_edit': '_onEditProfilePicClick',
        'change .o_forum_file_upload': '_onFileUploadChange',
        'click .o_forum_profile_pic_clear': '_onProfilePicClearClick',
        'click .o_forum_profile_bio_edit': '_onProfileBioEditClick',
        'click .o_forum_profile_bio_cancel_edit': '_onProfileBioCancelEditClick',
    },

    /**
     * @override
     */
    start: async function () {
        const def = this._super.apply(this, arguments);
        if (this.editableMode) {
            return def;
        }

        const $textarea = this.$("textarea.o_wysiwyg_loader");

        const options = {
            recordInfo: {
                context: this._getContext(),
                res_model: "res.users",
                res_id: parseInt(this.$("input[name=user_id]").val()),
            },
            resizable: true,
            userGeneratedContent: true,
        };

        if ($textarea[0].attributes.placeholder) {
            options.placeholder = $textarea[0].attributes.placeholder.value;
        }

        this._wysiwyg = await loadWysiwygFromTextarea(this, $textarea[0], options);

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
            $form.find('.o_wforum_avatar_img').attr('src', ev.target.result);
        };
        $form.find('#forum_clear_image').remove();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onProfilePicClearClick: function (ev) {
        var $form = $(ev.currentTarget).closest('form');
        $form.find('.o_wforum_avatar_img').attr('src', '/web/static/img/placeholder.png');
        $form.append($('<input/>', {
            name: 'clear_image',
            id: 'forum_clear_image',
            type: 'hidden',
        }));
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onProfileBioEditClick: function (ev) {
        ev.preventDefault();
        ev.currentTarget.classList.add("d-none");
        document.querySelector(".o_forum_profile_bio_cancel_edit").classList.remove("d-none");
        document.querySelector(".o_forum_profile_bio").classList.add("d-none");
        document.querySelector(".o_forum_profile_bio_form").classList.remove("d-none");
    },

     /**
     * @private
     * @param {Event} ev
     */
     _onProfileBioCancelEditClick: function (ev) {
        ev.preventDefault();
        ev.currentTarget.classList.add("d-none");
        document.querySelector(".o_forum_profile_bio_edit").classList.remove("d-none");
        document.querySelector(".o_forum_profile_bio_form").classList.add("d-none");
        document.querySelector(".o_forum_profile_bio").classList.remove("d-none");
     },
});

publicWidget.registry.websiteProfileNextRankCard = publicWidget.Widget.extend({
    selector: '.o_wprofile_progress_circle',

    /**
     * @override
     */
    start: function () {
        this.$('g[data-bs-toggle="tooltip"]').tooltip();
        return this._super.apply(this, arguments);
    },

});

export default publicWidget.registry.websiteProfile;
