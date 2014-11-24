(function () {
    'use strict';

    openerp.Tour.register({
        id:   'website_form_builder_tour',
        name: "Try to create some forms",
        path: '',
        mode: 'test',
        steps: [

        /*

            

        */
            {
                title:          "Launch Website Editor",
                element:        "button[data-action=edit]"
            },
            {
                title:          "Launch Snippet Menu",
                waitFor:        "button[data-action=snippet]",
                element:        "button[data-action=snippet]"
            },
            {
                title:          "Open Snippet Feature Tab",
                waitFor:        "a[href=#snippet_feature]",
                element:        "a[href=#snippet_feature]"
                
            },
            {
                title:          "Drop the form model on the website",
                snippet:        "#snippet_feature .oe_snippet[name='Form Builder']"
            },
            {
                title:          "Check if the snippet is drop and if the pop-up is popped",
                waitFor:        "body:has(form[action*='/website_form/'])"          +
                                ":has(.modal-body:has(select.form-select-action)"   +
                                    ":has(input[name=success]))"
            },
            {
                title:          "Change the action to create issues",
                element:        ".modal-body select",
                sampleText:     "project.issue"

            },
            {
                title:          "Change the action to Send an E-mail",
                waitFor:        ".modal-body .o_form-action-mailto:hidden",
                element:        ".modal-body select",
                sampleText:     "mail.mail"
            },
            {
                title:          "Open autocomplete E-mail suggestion",
                waitFor:        ".modal-body .o_form-action-mailto:visible",
                element:        ".modal-body div.text-arrow"
            },
            {
                title:          "Select tang@asustek.com",
                waitFor:        ".modal-body .text-suggestion:visible",
                element:        ".text-suggestion:contains(tang@asustek.com)"
            },
            {
                title:          "Valid the configuration",
                waitFor:        ".modal-body .text-suggestion:hidden",
                element:        ".modal-body button.validate"
            },
            {
                title:       "Edit current "
            }

/*
waitFor:   'label:contains(32 GB) input[checked]',
waitNot:   '#cart_products:contains("[A8767] Apple In-Ear Headphones")',
sampleText: '1',
*/
        ]
    });

}());
