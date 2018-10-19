odoo.define('website_links.code_editor', function (require) {
'use strict';

var sAnimations = require('website.content.snippets.animation');
var ajax = require('web.ajax');

sAnimations.registry.websiteLinksCodeEditor = sAnimations.Class.extend({
    selector: '.o_website_links_edit_code',
    read_events: {
        'click .o_website_links_edit_code': '_onEdit',
        'click .o_website_links_cancel_edit': '_onCancel',
        'submit #edit-code-form': '_onEditCodeForm',
        'click .o_website_links_ok_edit': '_onEditCodeForm'
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {String} new_code
     */
    _showNewCode: function (new_code) {
        $('.o_website_links_code_error').html('');
        $('.o_website_links_code_error').hide();

        $('#o_website_links_code form').remove();

        // Show new code
        var host = $('#short-url-host').html();
        $('#o_website_links_code').html(new_code);

        // Update button copy to clipboard
        $('.copy-to-clipboard').attr('data-clipboard-text', host + new_code);

        // Show action again
        $('.o_website_links_edit_code').show();
        $('.copy-to-clipboard').show();
        $('.o_website_links_edit_tools').hide();
    },
    /**
     * @private
     */
    _submitCode: function () {
        var init_code = $('#edit-code-form #init_code').val();
        var new_code = $('#edit-code-form #new_code').val();
        var self = this;

        if (new_code === '') {
            self.$('.o_website_links_code_error').html("The code cannot be left empty");
            self.$('.o_website_links_code_error').show();
            return;
        }

        this._showNewCode(new_code);

        if (init_code === new_code) {
            this._showNewCode(new_code);
        } else {
            ajax.jsonRpc('/website_links/add_code', 'call', {'init_code':init_code, 'new_code':new_code})
                .then(function (result) {
                    self._showNewCode(result[0].code);
                })
                .fail(function () {
                    $('.o_website_links_code_error').show();
                    $('.o_website_links_code_error').html("This code is already taken");
                });
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onEdit: function () {
        var init_code = $('#o_website_links_code').html();
        $('#o_website_links_code').html("<form style='display:inline;' id='edit-code-form'><input type='hidden' id='init_code' value='" + init_code + "'/><input type='text' id='new_code' value='" + init_code + "'/></form>");
        $('.o_website_links_edit_code').hide();
        $('.copy-to-clipboard').hide();
        $('.o_website_links_edit_tools').show();
    },
    /**
     * @override
     * @param {Object} e
     */
    _onCancel: function (e) {
        e.preventDefault();
        $('.o_website_links_edit_code').show();
        $('.copy-to-clipboard').show();
        $('.o_website_links_edit_tools').hide();
        $('.o_website_links_code_error').hide();

        var old_code = $('#edit-code-form #init_code').val();
        $('#o_website_links_code').html(old_code);

        $('#code-error').remove();
        $('#o_website_links_code form').remove();
    },
    /**
     * @override
     * @param {Object} e
     */
    _onEditCodeForm: function (e) {
        e.preventDefault();
        this._submitCode();
    },

});

});
