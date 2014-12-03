(function () {
    'use strict';

    openerp.Tour.register({
        id:   'website_form_builder_tour',
        name: "Try to create some forms",
        path: '',
        mode: 'test',
        steps: [

        /*

            DROP A FORM BUILDER SNIPPET AND CONFIGURE IT

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
                element:        ".modal-body a.select2-choice"
            },
            {
                title:          "Put a custom e-mail",
                waitFor:        ".select2-search .select2-input",
                element:        ".select2-search .select2-input",
                sampleText:     "john@smith.com"
            },
            {
                title:          "Select added e-mail",
                waitFor:        ".select2-result-selectable",
                element:        ".select2-result-selectable"
            },
            {
                title:          "Valid the configuration",
                waitFor:        ".select2-results:hidden",
                element:        ".modal-footer button.validate"
            },

        /*

            DROP AN INPUT TEXT SNIPPET AND CONFIGURE IT

        */

            {
                title:          "Put a text field snippet",
                waitFor:        "#snippet_form .oe_snippet[name='Input Text']",
                snippet:        "#snippet_form .oe_snippet[name='Input Text']"
            },
            {
                title:          "Select a DB field for this input snippet",
                waitFor:        ".modal-title .field_name:contains('Text Field')",
                element:        ".modal-body .form-select-field",
                sampleText:     "display_name"
            },
            {
                title:          "Change the label",
                element:        ".modal-body .form-field-label",
                sampleText:     "Name"
            },
            {
                title:          "Change the placeholder",
                element:        ".modal-body .form-field-placeholder",
                sampleText:     "John Smith"
            },
            {
                title:          "Change the prefix",
                element:        ".modal-body .form-field-prepend",
                sampleText:     "Mr."
            },
            {
                title:          "Change the sufix",
                element:        ".modal-body .form-field-append",
                sampleText:     "."
            },
            {
                title:          "Change the help text",
                element:        ".modal-body .form-field-help",
                sampleText:     "Read the word witch following 'name' on your IDCard and write it on the input"
            },
            {
                title:          "Make this input required",
                element:        ".modal-body .form-field-required",
                sampleText:     "checked"
            },
            {
                title:          "Valid the configuration for input text",
                element:        ".modal-footer input.validate"
            },
            {
                title:          "Check the builded snippet",
                waitingFor:     ".form-group"                           +
                                ":has(span.prepend:contains(Mr.))"      +
                                ":has(span.append:contains(.))"         +
                                ":has(input[type=text][name=display_name][placeholder='John Smith'][id=display_name])" +
                                ":has(label:contains(Name))" +
                                ":has(.help-block:contains('Read the word witch following 'name' on your IDCard and write it on the input'))"
            },

        /*

            DROP AN INPUT TEXT SNIPPET AND CONFIGURE IT

        */

            {
                title:          "Put a hidden input snippet",
                waitFor:        "#snippet_form .oe_snippet[name='Input Hidden']",
                snippet:        "#snippet_form .oe_snippet[name='Input Hidden']"
            },
            {
                title:          "Select a DB field for this input snippet",
                waitFor:        ".modal-title .field_name:contains('Hidden Field')",
                element:        ".modal-body .form-select-field",
                sampleText:     "record_name"
            },
            {
                title:          "Change the label",
                element:        ".modal-body .form-field-label",
                sampleText:     "Name"
            },
            {
                title:          "Change the value",
                element:        ".modal-body .form-field-value",
                sampleText:     "John Smith's Message"
            },
            {
                title:          "Valid the configuration for input text",
                element:        ".modal-footer input.validate"
            },


            {
                title:          "Usless step",
                waitFor:        "html"
            }

        ]
    });

}());
