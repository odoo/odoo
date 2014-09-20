(function () {
    'use strict';
    var website = openerp.website;

    website.if_dom_contains('#email_designer', function () {
        website.snippet.BuildingBlock.include({
            _get_snippet_url: function () {
                return '/website_mail/snippets';
            }
        });

        $('.js_template_set').click(function(ev) {
            // Copy the template to the body of the email
            $('#email_designer').show();
            $('#email_template').hide();
            $(".js_content", $(this).parent()).children().clone().appendTo('#email_body');
            $(".js_content", $(this).parent()).children().clone().appendTo('#email_body_html');
            $('#email_body').addClass('oe_dirty');
            $('#email_body_html').addClass('oe_dirty');

            openerp.website.editor_bar.edit();
            event.preventDefault();
        });
    });

})();
