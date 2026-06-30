/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.websiteLinksCodeEditor = publicWidget.Widget.extend({
    selector: '#wrapwrap:has(.o_website_links_edit_code)',
    events: {
        'click .o_website_links_edit_code': '_onEditCodeClick',
        'click .o_website_links_cancel_edit': '_onCancelEditClick',
        'submit #edit-code-form': '_onEditCodeFormSubmit',
        'click .o_website_links_ok_edit': '_onEditCodeFormSubmit',
    },

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {String} newCode
     */
    _showNewCode: function (newCode) {
        $('.o_website_links_code_error').html('');
        $('.o_website_links_code_error').hide();

        $('#o_website_links_code form').remove();

        // Show new code
        var host = $('#short-url-host').html();
        $('#o_website_links_code').html(newCode);

        // Update button copy to clipboard
        $('.copy-to-clipboard').attr('data-clipboard-text', host + newCode);

        // Show action again
        $('.o_website_links_edit_code').show();
        $('.copy-to-clipboard').show();
        $('.o_website_links_edit_tools').hide();
    },
    /**
     * @private
     * @returns {Promise}
     */
    _submitCode: function () {
        var initCode = $('#edit-code-form #init_code').val();
        var newCode = $('#edit-code-form #new_code').val();
        var self = this;

        if (newCode === '') {
            self.$('.o_website_links_code_error').html(_t("The code cannot be left empty"));
            self.$('.o_website_links_code_error').show();
            return;
        }

        this._showNewCode(newCode);

        if (initCode === newCode) {
            this._showNewCode(newCode);
        } else {
            return this.rpc('/website_links/add_code', {
                init_code: initCode,
                new_code: newCode,
            }).then(function (result) {
                self._showNewCode(result[0].code);
            }, function () {
                $('.o_website_links_code_error').show();
                $('.o_website_links_code_error').html(_t("This code is already taken"));
            });
        }

        return Promise.resolve();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onEditCodeClick: function () {
        var initCode = $('#o_website_links_code').html();
        $('#o_website_links_code').html('<form style="display:inline;" id="edit-code-form"><input type="hidden" id="init_code" value="' + initCode + '"/><input type="text" id="new_code" value="' + initCode + '"/></form>');
        $('.o_website_links_edit_code').hide();
        $('.copy-to-clipboard').hide();
        $('.o_website_links_edit_tools').show();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onCancelEditClick: function (ev) {
        ev.preventDefault();
        $('.o_website_links_edit_code').show();
        $('.copy-to-clipboard').show();
        $('.o_website_links_edit_tools').hide();
        $('.o_website_links_code_error').hide();

        var oldCode = $('#edit-code-form #init_code').val();
        $('#o_website_links_code').html(oldCode);

        $('#code-error').remove();
        $('#o_website_links_code form').remove();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onEditCodeFormSubmit: function (ev) {
        ev.preventDefault();
        this._submitCode();
    },
});
