import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import { loadWysiwygFromTextarea } from "@web_editor/js/frontend/loadWysiwygFromTextarea";
import { redirect } from "@web/core/utils/urls";

publicWidget.registry.websiteProfile = publicWidget.Widget.extend({
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
        const element = ev.currentTarget;
        rpc('/profile/send_validation_email', {
            redirect_url: element.dataset["redirect_url"],
        }).then(function (data) {
            if (data) {
                redirect(element.dataset["redirect_url"]);
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
