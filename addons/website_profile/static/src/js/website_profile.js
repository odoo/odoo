/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import { loadWysiwygFromTextarea } from "@web_editor/js/frontend/loadWysiwygFromTextarea";
import { redirect } from "@web/core/utils/urls";

publicWidget.registry.websiteProfile = publicWidget.Widget.extend({
    selector: '.o_wprofile_email_validation_container',
    read_events: {
        'click .send_validation_email': 'async _onSendValidationEmailClick',
        'close.bs.alert div:has(button.validated_email_close)': '_onCloseValidatedEmailClick',
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
        const element = ev.currentTarget;
        return rpc('/profile/send_validation_email', {
            redirect_url: element.dataset["redirect_url"],
        }).then(function (data) {
            if (data) {
                redirect(element.dataset["redirect_url"]);
                return new Promise(() => {});
            }
        });
    },

    /**
     * @private
     */
    _onCloseValidatedEmailClick: function () {
        rpc('/profile/validate_email/close');
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

        const textareaEl = this.el.querySelector("textarea.o_wysiwyg_loader");

        const options = {
            recordInfo: {
                context: this._getContext(),
                res_model: "res.users",
                res_id: parseInt(this.el.querySelector("input[name=user_id]").value),
            },
            value: textareaEl.getAttribute("content"),
            resizable: true,
            userGeneratedContent: true,
        };

        if (textareaEl.attributes.placeholder) {
            options.placeholder = textareaEl.attributes.placeholder.value;
        }

        this._wysiwyg = await loadWysiwygFromTextarea(this, textareaEl, options);

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
        ev.currentTarget.closest("form").querySelector(".o_forum_file_upload").click();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onFileUploadChange: function (ev) {
        if (!ev.currentTarget.files.length) {
            return;
        }
        const formEl = ev.currentTarget.closest("form");
        var reader = new window.FileReader();
        reader.readAsDataURL(ev.currentTarget.files[0]);
        reader.onload = function (ev) {
            formEl.querySelector(".o_wforum_avatar_img").src = ev.target.result;
        };
        formEl.querySelector("#forum_clear_image")?.remove();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onProfilePicClearClick: function (ev) {
        const formEl = ev.currentTarget.closest("form");
        formEl.querySelector(".o_wforum_avatar_img").src = "/web/static/img/placeholder.png";
        const inputElement = document.createElement("input");
        inputElement.setAttribute("name", "clear_image");
        inputElement.setAttribute("id", "forum_clear_image");
        inputElement.setAttribute("type", "hidden");
        formEl.append(inputElement);
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
        new Tooltip(this.el.querySelector('g[data-bs-toggle="tooltip"]'));
        return this._super.apply(this, arguments);
    },

});

export default publicWidget.registry.websiteProfile;
