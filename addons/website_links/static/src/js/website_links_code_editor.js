/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.websiteLinksCodeEditor = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    selectorHas: '.o_website_links_edit_code',
    events: {
        'click .copy-to-clipboard': '_onCopyToClipboardClick',
        'click .o_website_links_edit_code': '_onEditCodeClick',
        'click .o_website_links_cancel_edit': '_onCancelEditClick',
        'submit #edit-code-form': '_onEditCodeFormSubmit',
        'click .o_website_links_ok_edit': '_onEditCodeFormSubmit',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onCopyToClipboardClick: async function (ev) {
        ev.preventDefault();
        const copyBtn = ev.currentTarget;
        const tooltip = Tooltip.getOrCreateInstance(copyBtn, {
            title: _t("Link Copied!"),
            trigger: "manual",
            placement: "right",
        });
        setTimeout(
            async () => await browser.navigator.clipboard.writeText(copyBtn.dataset.clipboardText)
        );
        tooltip.show();
        setTimeout(() => tooltip.hide(), 1200);
    },

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
            return rpc('/website_links/add_code', {
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
