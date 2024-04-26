/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.websiteLinksCodeEditor = publicWidget.Widget.extend({
    selector: '#wrapwrap:has(.o_website_links_edit_code)',
    events: {
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
     * @param {String} newCode
     */
    _showNewCode: function (newCode) {
        document.querySelector('.o_website_links_code_error').innerHTML = '';
        document.querySelector('.o_website_links_code_error').style.display = 'none';

        document.querySelector('#o_website_links_code form').remove();

        // Show new code
        const host = document.querySelector('#short-url-host').innerHTML;
        document.querySelector('#o_website_links_code').innerHTML = newCode;

        // Update button copy to clipboard
        document.querySelector('.copy-to-clipboard').setAttribute('data-clipboard-text', host + newCode);

        // Show action again
        document.querySelector('.o_website_links_edit_code').style.display = '';
        document.querySelector('.copy-to-clipboard').style.display = '';
        document.querySelector('.o_website_links_edit_tools').style.display = 'none';
    },
    /**
     * @private
     * @returns {Promise}
     */
    _submitCode: function () {
        const initCode = document.querySelector('#edit-code-form #init_code').value;
        const newCode = document.querySelector('#edit-code-form #new_code').value;
        const self = this;

        if (newCode === '') {
            self.el.querySelector('.o_website_links_code_error').innerHTML = _t("The code cannot be left empty");
            self.el.querySelector('.o_website_links_code_error').style.display = '';
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
                document.querySelector('.o_website_links_code_error').style.display = '';
                document.querySelector('.o_website_links_code_error').innerHTML = _t("This code is already taken");
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
        const initCode = document.querySelector('#o_website_links_code').innerHTML;
        document.querySelector('#o_website_links_code').innerHTML = '<form style="display:inline;" id="edit-code-form"><input type="hidden" id="init_code" value="' + initCode + '"/><input type="text" id="new_code" value="' + initCode + '"/></form>';
        document.querySelector('.o_website_links_edit_code').hide();
        document.querySelector('.copy-to-clipboard').hide();
        document.querySelector('.o_website_links_edit_tools').show();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onCancelEditClick: function (ev) {
        ev.preventDefault();
        document.querySelector('.o_website_links_edit_code').show();
        document.querySelector('.copy-to-clipboard').show();
        document.querySelector('.o_website_links_edit_tools').hide();
        document.querySelector('.o_website_links_code_error').hide();

        const oldCode = document.querySelector('#edit-code-form #init_code').val();
        document.querySelector('#o_website_links_code').innerHTML = oldCode;

        document.querySelector('#code-error').remove();
        document.querySelector('#o_website_links_code form').remove();
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
