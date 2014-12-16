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
                waitFor:        ".form-group[data-form=input]"          +
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
                title:          "Check the builded snippet",
                waitFor:        ".form-group[data-form=hidden]"                                                 +
                                ":has(input[type=hidden][name=record_name][value='John Smith's Message'])"      +
                                ":visible"
            },


        /*

            DROP A TEXTAREA SNIPPET AND CONFIGURE IT

        */

            {
                title:          "Put a textarea snippet",
                waitFor:        "#snippet_form .oe_snippet[name='Textarea']",
                snippet:        "#snippet_form .oe_snippet[name='Textarea']"
            },
            {
                title:          "Select a DB field for this input snippet",
                waitFor:        ".modal-title .field_name:contains('Textarea')",
                element:        ".modal-body .form-select-field",
                sampleText:     "body_html"
            },
            {
                title:          "Change the label",
                element:        ".modal-body .form-field-label",
                sampleText:     "Your Message"
            },
            {
                title:          "Change the placeholder",
                element:        ".modal-body .form-field-placeholder",
                sampleText:     "This is my usless e-mail"
            },
            {
                title:          "Change the help text",
                element:        ".modal-body .form-field-help",
                sampleText:     "Write what you want to say"
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
                waitFor:        ".form-group[data-form=textarea]"       +
                                ":has(textarea[name=body_html][placeholder='This is my usless e-mail'][id=body_html][required])" +
                                ":has(label:contains('Your Message'))"            +
                                ":has(.help-block:contains('Write what you want to say'))",
            },


/*

            DROP A CHECKBOX SNIPPET AND CONFIGURE IT

        */

            {
                title:          "Put a Checkbox snippet",
                waitFor:        "#snippet_form .oe_snippet[name='Checkbox']",
                snippet:        "#snippet_form .oe_snippet[name='Checkbox']"
            },
            {
                title:          "Select a DB field for this input snippet",
                waitFor:        ".modal-title .field_name:contains('Checkbox Field')",
                element:        ".modal-body .form-select-field",
                sampleText:     "custom"
            },
            {
                title:          "Change the label",
                element:        ".modal-body .form-field-label",
                sampleText:     "Products"
            },
            {
                title:          "Create Product List",
                element:        ".modal-body .option-label:eq(0)",
                sampleText:     "Iphone"
            },
            {
                title:          "Create Product List",
                element:        ".modal-body .option-value:eq(0)",
                sampleText:     "iphone"
            },
            {
                title:          "Create Product List",
                element:        ".modal-body .o_form-editor-add td:first",
            },
            {
                title:          "Create Product List",
                element:        ".modal-body .option-label:eq(1)",
                sampleText:     "Galaxy S"
            },
            {
                title:          "Create Product List",
                element:        ".modal-body .option-value:eq(1)",
                sampleText:     "galaxy S"
            },
            {
                title:          "Create Product List",
                element:        ".modal-body .o_form-editor-add td:first",
            },
            {
                title:          "Create Product List",
                element:        ".modal-body .option-label:eq(2)",
                sampleText:     "Xperia"
            },
            {
                title:          "Create Product List",
                element:        ".modal-body .option-value:eq(2)",
                sampleText:     "Xperia"
            },
            {
                title:          "Make this input required",
                element:        ".modal-body .form-field-inline",
                sampleText:     "checked"
            },
            {
                title:          "Make this input required",
                element:        ".modal-body .form-field-required",
                sampleText:     "checked"
            },
            {
                title:          "Valid the configuration for checkbox",
                element:        ".modal-footer input.validate"
            },
            {
                title:          "Check the builded snippet",
                waitFor:        ".form-group[data-form=checkbox]"       +
                                ":has(div[name=Products][id=Products])" +
                                ":has(div.div-inline)"                  +
                                ":has(label:contains('Products'))"      +
                                ":has(label:contains('Iphone'))"        +
                                ":has(label:contains('Galaxy S'))"      +
                                ":has(label:contains('Xperia'))"        +
                                ":has(input[type=checkbox][id=Products-0][name=Products][value='iphone'])" +
                                ":has(input[type=checkbox][id=Products-1][name=Products][value='galaxy S'])" +
                                ":has(input[type=checkbox][id=Products-2][name=Products][value='Xperia'])" +
                                ":not(.help-block:visible)",
            },


/*

            DROP A RADIO SNIPPET AND CONFIGURE IT

        */

            {
                title:          "Put a Radio snippet",
                waitFor:        "#snippet_form .oe_snippet[name='Radios']",
                snippet:        "#snippet_form .oe_snippet[name='Radios']"
            },
            {
                title:          "Select a DB field for this input snippet",
                waitFor:        ".modal-title .field_name:contains('Radio Field')",
                element:        ".modal-body .form-select-field",
                sampleText:     "custom"
            },
            {
                title:          "Change the label",
                element:        ".modal-body .form-field-label",
                sampleText:     "Service"
            },
            {
                title:          "Create Product List",
                element:        ".modal-body .option-label:eq(0)",
                sampleText:     "Service Après Vente"
            },
            {
                title:          "Create Product List",
                element:        ".modal-body .option-value:eq(0)",
                sampleText:     "S.A.V."
            },
            {
                title:          "Create Product List",
                element:        ".modal-body .o_form-editor-add td:first",
            },
            {
                title:          "Create Product List",
                element:        ".modal-body .option-label:eq(1)",
                sampleText:     "Service Facturation"
            },
            {
                title:          "Create Product List",
                element:        ".modal-body .option-value:eq(1)",
                sampleText:     "S.F."
            },
            {
                title:          "Make this input required",
                element:        ".modal-body .form-field-inline",
                sampleText:     "checked"
            },
            {
                title:          "Valid the configuration for checkbox",
                element:        ".modal-footer input.validate"
            },
            {
                title:          "Check the builded snippet",
                waitFor:        ".form-group[data-form=radio]"                     +
                                ":has(div.div-inline)"                             +
                                ":has(label:contains('Service'))"                  +
                                ":has(label:contains('Service Après Vente'))"      +
                                ":has(label:contains('Service Facturation'))"      +
                                ":has(input[type=radio][id=Service-0][name=Service][value='S.A.V.'])"  +
                                ":has(input[type=radio][id=Service-1][name=Service][value='S.F.'])"    +
                                ":not([required])" +
                                ":not(.help-block:visible)",
            },

/*

            DROP A SELECT SNIPPET AND CONFIGURE IT

        */

            {
                title:          "Put a Radio snippet",
                waitFor:        "#snippet_form .oe_snippet[name='Select']",
                snippet:        "#snippet_form .oe_snippet[name='Select']"
            },
            {
                title:          "Select a DB field for this input snippet",
                waitFor:        ".modal-title .field_name:contains('Select Field')",
                element:        ".modal-body .form-select-field",
                sampleText:     "custom"
            },
            {
                title:          "Change the label",
                element:        ".modal-body .form-field-label",
                sampleText:     "State"
            },
            {
                title:          "Create Product List",
                element:        ".modal-body .option-label:eq(0)",
                sampleText:     "Belgium"
            },
            {
                title:          "Create Product List",
                element:        ".modal-body .option-value:eq(0)",
                sampleText:     "be"
            },
            {
                title:          "Create Product List",
                element:        ".modal-body .o_form-editor-add td:first",
            },
            {
                title:          "Create Product List",
                element:        ".modal-body .option-label:eq(1)",
                sampleText:     "France"
            },
            {
                title:          "Create Product List",
                element:        ".modal-body .option-value:eq(1)",
                sampleText:     "fr"
            },
            {
                title:          "Make this input required",
                element:        ".modal-body .form-field-multiple",
                sampleText:     "checked"
            },
            {
                title:          "Make this input required",
                element:        ".modal-body .form-field-autocomplete",
                sampleText:     "checked"
            },
            {
                title:          "Valid the configuration for checkbox",
                element:        ".modal-footer input.validate"
            },
            {
                title:          "Check the builded snippet",
                waitFor:        ".form-group[data-form=select]"                    +
                                ":has(label:contains('State'))"                    +
                                ":has(option[value=be]:contains('Belgium'))"       +
                                ":has(option[value=fr]:contains('France'))"        +
                                ":has(select[id=State][name=State][multiple][autocomplete=on])"  +
                                ":not([required])" +
                                ":not(.help-block:visible)",
            },
        /*

            DROP A Upload field SNIPPET AND CONFIGURE IT

        */

            {
                title:          "Put upload field snippet",
                waitFor:        "#snippet_form .oe_snippet[name='Upload Field']",
                snippet:        "#snippet_form .oe_snippet[name='Upload Field']"
            },
            {
                title:          "Select a DB field for this input snippet",
                waitFor:        ".modal-title .field_name:contains('Upload Field')",
                element:        ".modal-body .form-select-field",
                sampleText:     "attachment_ids"
            },
            {
                title:          "Change the label",
                element:        ".modal-body .form-field-label",
                sampleText:     "Invoice Scan"
            },
            {
                title:          "Change the Button Label",
                element:        ".modal-body .form-button-label",
                sampleText:     "Select an Invoice"
            },
            {
                title:          "Change the help text",
                element:        ".modal-body .form-field-help",
                sampleText:     "Upload a scan of your invoice"
            },
            {
                title:          "Valid the configuration for upload",
                element:        ".modal-footer input.validate"
            },
            {
                title:          "Check the builded snippet",
                waitFor:        ".form-group[data-form=inputfile]"       +
                                ":has(.browse-label:contains('Select an Invoice'))" +
                                ":has(input[type=file][multiple=multiple][id=attachment_ids][name=attachment_ids])" +
                                ":has(label:contains('Invoice Scan'))" +
                                ":not([required])" +
                                ":has(.help-block:contains('Upload a scan of your invoice'))"
            },
            {
                title:          "Save the form",
                element:        "button[data-action=save]"
            },
            {
                title:          "wait...",
                waitFor:        "html"
            },
            {
                title:          "exit the admin mode 1/2",
                waitFor:        "a.dropdown-toggle:has(span:contains('Administrator'))",
                element:        "a.dropdown-toggle:has(span:contains('Administrator'))"
            },
            {
                title:          "exit the admin mode 2/2",
                waitFor:        "a[href='/web/session/logout?redirect=/']:visible",
                element:        "a[href='/web/session/logout?redirect=/']"
            },
            {
                title:          "wait for logout",
                waitFor:        "a[href='/web/login']"
            },
            {
                title:          "Try to send empty form",
                waitFor:        "form[action='/website_form/mail.mail']" +
                                "[data-model='mail.mail']" +
                                "[data-success='']" +
                                "[data-model-name='Outgoing Mails']" +
                                "[data-default-field='Rich-text Contents']" +
                                ":has(label:contains('Name'))" +
                                ":has(label:contains('Invoice Scan'))" +
                                ":has(label:contains('Your Message'))" +
                                ":has(label:contains('Products'))" +
                                ":has(label:contains('Service'))" +
                                ":has(label:contains('State'))" +
                                ":has(input[type=hidden][name=record_name][value='John Smith's Message'])" +
                                ":has(div[data-form=hidden]:hidden)",
                element:        ".o_send_button"
            },
            {
                title:          "Check if required fields was detected and complete the Name field",
                waitFor:        ".has-error:has(input[name=display_name])",
                element:        "input[name=display_name]",
                sampleText:     "Janne Smith"
            },
            {
                title:          "Check if required fields was detected and complete the Message field",
                waitFor:        ".has-error:has(textarea[name=body_html])",
                element:        "textarea[name=body_html]",
                sampleText:     "My more usless message"
            },
            {
                title:          "Check if required fields was detected and complete the Products field",
                waitFor:        ".has-error:has(div[name=Products])",
                element:        "input[id=Products-1]"
            },
            {
                title:          "check another product",
                element:        "input[id=Products-2]"
            },
            {
                title:          "Check if Valid fields was detected",
                waitFor:        ".has-success:has(div[name=Service])",
                element:        "input[id=Service-1]"
            },
            {
                title:          "Check if empty fields was detected",
                waitFor:        ".has-warning:has(select[name=State])",
                element:        "select[name=State]",
                sampleText:     "be"
            },
            {
                title:          "Check if empty fields was detected",
                waitFor:        ".has-warning:has(input[name=attachment_ids])"
            },
            {
                title:          "Check if empty fields was detected",
                waitFor:        ".has-warning:has(input[name=contact_name])"
            },
            {
                title:          "Send the form",
                element:        ".o_send_button"
            },
            {
                title:          "check if the form is submited without errors",
                waitFor:        "form.o_send-success:has(.alert-success:visible):has(.alert-danger:hidden)"
            },


            /*

            TEST THE CONTACT US FORM 

            */

            {
                title:          "Go to contact us form",
                element:        "a[href='/page/website.contactus']"
            },
            {
                title:          "Complete name",
                element:        "#contact_name",
                sampleText:     "John Smith"
            },
            {
                title:          "Complete phone number",
                element:        "input[name=phone]",
                sampleText:     "118.218"
            },
            {
                title:          "Complete Email",
                element:        "#email_from",
                sampleText:     "john@smith.com"
            },
            {
                title:          "Complete Subject",
                element:        "input[name=name]",
                sampleText:     "Usless Message"
            },
            {
                title:          "Complete Subject",
                element:        "textarea[name=description]",
                sampleText:     "The complete usless Message"
            },
            {
                title:          "Send the form",
                element:        ".o_send_button"
            },
            {
                title:          "check if the form is submited without errors",
                waitFor:        "form.o_send-success:has(.alert-success:visible):has(.alert-danger:hidden)"
            },
   /*

            TEST THE HR APPLICANTS FORM 

            */
            
            {
                title:          "Go to Job Page",
                element:        "a[href='/jobs']"
            },
            {
                title:          "Go to Experienced Developper posts",
                element:        "a[href='/jobs/detail/experienced-developer-4']"
            },
            {
                title:          "Go to Application Form",
                element:        "a[href='/jobs/apply/4']"
            },
            {
                title:          "Complete name",
                element:        "input[name=partner_name]",
                sampleText:     "John Smith"
            },
            {
                title:          "Complete phone number",
                element:        "input[name=partner_phone]",
                sampleText:     "118.218"
            },
            {
                title:          "Complete Email",
                element:        "input[name=email_from]",
                sampleText:     "john@smith.com"
            },
            {
                title:          "Complete Subject",
                element:        "textarea[name=description]",
                sampleText:     "The complete usless Message"
            },
            {
                title:          "Send the form",
                element:        ".o_send_button"
            },
            {
                title:          "check if the form is submited without errors",
                waitFor:        "form.o_send-success:has(.alert-success:visible):has(.alert-danger:hidden)"
            },
            {
                title:          "Login",
                element:        "a[href='/web/login']"
            },
            {
                title:          "Insert user name",
                element:        "input[name=login]",
                sampleText:     "admin"
            },
            {
                title:          "Insert user password",
                element:        "input[name=password]",
                sampleText:     "admin"
            },
            {
                title:          "Login",
                element:        "button[type=submit]:contains('Log in')"
            },
            {
                title:          "Check results on the DB",
                onload: function (tour) {
                    var success = function(v1, v2, v3) {
                        console.log(v1, v2, v3);
                        if(v1.length && v2.length && v3.length) {
                            $('body').append('<div id="website_form_builder_success_test_tour"></div>');
                        }
                    };

                    var mailDef =   new openerp.Model(openerp.website.session,"mail.mail")
                                    .call(  "search_read",
                                            [[
                                                ['body_html', 'like', 'My more usless message'],
                                                ['body_html', 'like', 'Service : S.F.'],
                                                ['body_html', 'like', 'State : be'],
                                                ['body_html', 'like', 'Products : galaxy S,Xperia']
                                            ],[]],
                                            {context: openerp.website.get_context()});

                    var leadDef =   new openerp.Model(openerp.website.session,"crm.lead")
                                    .call(  "search_read",
                                            [[
                                                ['contact_name', '='   , 'John Smith'],
                                                ['phone'       , '='   , '118.218'],
                                                ['email_from'  , '='   , 'john@smith.com'],
                                                ['name'        , '='   , 'Usless Message'],
                                                ['description' , 'like', 'The complete usless Message']
                                            ],[]],
                                            {context: openerp.website.get_context()});

                    var hrDef   =   new openerp.Model(openerp.website.session,"hr.applicant")
                                    .call(  "search_read",
                                            [[
                                                ['partner_name'    , '='   , 'John Smith'],
                                                ['partner_phone'   , '='   , '118.218'],
                                                ['email_from'      , '='   , 'john@smith.com'],
                                                ['description'     , 'like', 'The complete usless Message']
                                            ],[]],
                                            {context: openerp.website.get_context()});

                    $.when(mailDef,leadDef,hrDef).then(success);
                }
            },
            {
                title:          "Check if data is correctly inserted",
                waitFor:        "#website_form_builder_success_test_tour"
            },
            {
                title:          "Final Step",
                waitFor:        "html"
            }
        ]
    });

}());
