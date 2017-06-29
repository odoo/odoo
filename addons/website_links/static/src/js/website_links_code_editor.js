odoo.define('website_links.code_editor', function (require) {
'use strict';

require('web.dom_ready');
var ajax = require('web.ajax');

if (!$('.o_website_links_edit_code').length) {
    return $.Deferred().reject("DOM doesn't contain '.o_website_links_edit_code'");
}

    // Edit the short URL code
    $('.o_website_links_edit_code').on('click', function (e) {
        e.preventDefault();

        var init_code = $('#o_website_links_code').html();

        $('#o_website_links_code').html("<form style='display:inline;' id='edit-code-form'><input type='hidden' id='init_code' value='" + init_code + "'/><input type='text' id='new_code' value='" + init_code + "'/></form>");
        $('.o_website_links_edit_code').hide();
        $('.copy-to-clipboard').hide();
        $('.o_website_links_edit_tools').show();

        $('.o_website_links_cancel_edit').on('click', function (e) {
            e.preventDefault();

            $('.o_website_links_edit_code').show();
            $('.copy-to-clipboard').show();
            $('.o_website_links_edit_tools').hide();
            $('.o_website_links_code_error').hide();

            var old_code = $('#edit-code-form #init_code').val();
            $('#o_website_links_code').html(old_code);

            $('#code-error').remove();
            $('#o_website_links_code form').remove();
        });

        function submit_code() {
            var init_code = $('#edit-code-form #init_code').val();
            var new_code = $('#edit-code-form #new_code').val();

            if (new_code === '') {
                self.$('.o_website_links_code_error').html("The code cannot be left empty");
                self.$('.o_website_links_code_error').show();
                return;
            }

            function show_new_code(new_code) {
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
            }

            if (init_code === new_code) {
                show_new_code(new_code);
            }
            else {
                ajax.jsonRpc('/website_links/add_code', 'call', {'init_code':init_code, 'new_code':new_code})
                    .then(function (result) {
                        show_new_code(result[0].code);
                    })
                    .fail(function () {
                        $('.o_website_links_code_error').show();
                    $('.o_website_links_code_error').html("This code is already taken");
                    }) ;
            }
        }

        $('#edit-code-form').submit(function (e) {
            e.preventDefault();
            submit_code();
        });

        $('.o_website_links_ok_edit').click(function (e) {
            e.preventDefault();
            submit_code();
        });
    });
});
