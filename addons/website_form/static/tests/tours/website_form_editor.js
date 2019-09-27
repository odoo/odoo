odoo.define('website_form_editor.tour', function(require) {
    'use strict';

    var rpc = require('web.rpc');
    var tour = require("web_tour.tour");

    tour.register("website_form_editor_tour", {
        test: true,
    }, [
        // Drop a form builder snippet and configure it
        {
            content:  "Enter edit mode",
            trigger:  "a[data-action=edit]"
        },
        {
            content:  "Drop the form snippet",
            trigger:  "#oe_snippets .oe_snippet:has(.s_website_form) .oe_snippet_thumbnail",
            run:      "drag_and_drop #wrap",
        },
        {
            content:  "Check dropped snippet",
            trigger:  "body:has(form[action*='/website_form/'])",
        },
        {
            content:  "Check if the snippet is dropped and if the modal is opened",
            trigger:  "body:has(form[action*='/website_form/'])" +
                      ":has(.modal-body:has(select[name='model_selection'])" +
                      ":has(input[name='success_page']))",
            run: function () {},
            in_modal: false,
        },
        {
            content:  "Change the action to create issues",
            trigger:  ".modal-body select",
            run:      "text project.issue"
        },
        {
            content:  "Change the action to Send an E-mail",
            trigger:  ".modal-body select",
            run: function (actions) {
                actions.text($('select[name="model_selection"] option:contains("Send an E-mail")').val());
            }
        },
        {
            content:  "Complete Recipient E-mail",
            extra_trigger:  ".modal-body input[name='email_to']",
            trigger:  ".modal-body input[name='email_to']",
            run:      "text test@test.test"
        },
        {
            content:  "Click on Save",
            trigger:  ".modal-footer button:first"
        },
        // Add the date field
        {
            content:  "Click on Form snippet",
            trigger:  ".s_website_form[data-model_name]"
        },
        {
            content:  "Click on Add a model field",
            trigger:  "[data-website_form_field_modal]"
        },
        {
            content:  "Select the date field",
            trigger:  "select[name='field_selection']",
            run:      "text date"
        },
        {
            content:  "Click on Save",
            trigger:  ".modal-footer button:first"
        },

        // Customize date field
        {
            content:  "Change the label",
            trigger:  ".col-form-label[for='date']",
            run:      "text Test Date"
        },
        {
            content:  "Click on Required",
            trigger:  "[data-website_form_field_require]"
        },
        {
            content:  "Check the resulting field",
            trigger:  ".form-field.o_website_form_required_custom" +
                            ":has(input[type=text][name=date][required])" +
                            ":has(label:contains('Test Date'))",
            run:      function () {},
        },

        // Add record_name field
        {
            content:  "Click on Form snippet",
            trigger:  ".s_website_form[data-model_name]"
        },
        {
            content:  "Click on Add a model field",
            trigger:  "[data-website_form_field_modal]"
        },
        {
            content:  "Select the record_name field",
            trigger:  "select[name='field_selection']",
            run:      "text record_name"
        },
        {
            content:  "Click on Save",
            trigger:  ".modal-footer button:first"
        },

        // Customize record_name field
        {
            content:  "Change the label",
            trigger:  ".col-form-label[for='record_name']",
            run:      "text Awesome Label"
        },
        {
            content:  "Click on Hidden",
            trigger:  "[data-toggle-class='o_website_form_field_hidden']"
        },
        {
            content:  "Check the resulting field",
            trigger:  ".form-field.o_website_form_field_hidden" +
                            ":has(input:not([required])[type=text][name=record_name])" +
                            ":has(label:contains('Awesome Label'))",
            run:      function () {},
        },


        // Add body_html field
        {
            content:  "Click on Form snippet",
            trigger:  ".s_website_form[data-model_name]"
        },
        {
            content:  "Click on Add a model field",
            trigger:  "[data-website_form_field_modal]"
        },
        {
            content:  "Select the body_html field",
            trigger:  "select[name='field_selection']",
            run:      "text body_html"
        },
        {
            content:  "Click on Save",
            trigger:  ".modal-footer button:first"
        },

        // Customize subject field
        {
            content:  "Change the label",
            trigger:  ".col-form-label[for='body_html']",
            run:      "text Your Message"
        },
        {
            content:  "Click on Required",
            trigger:  "[data-website_form_field_require]"
        },
        {
            content:  "Check the resulting field",
            trigger:  ".form-field.o_website_form_required_custom" +
                            ":has(textarea[name=body_html][required])" +
                            ":has(label:contains('Your Message'))",
            run:      function () {},
        },

        // Add recipient_ids relational field
        {
            content:  "Click on Form snippet",
            trigger:  ".s_website_form[data-model_name]"
        },
        {
            content:  "Click on Add a model field",
            trigger:  "[data-website_form_field_modal]"
        },
        {
            content:  "Select the recipient_ids field",
            trigger:  "select[name='field_selection']",
            run:      "text recipient_ids"
        },
        {
            content:  "Click on Save",
            trigger:  ".modal-footer button:first"
        },
        {
            content:  "Check the resulting field",
            trigger:  ".form-field:has(.col-form-label:contains('To (Partners)'))",
            run:      function () {},
        },

        // Add a custom multiple checkboxes field
        {
            content:  "Click on Form snippet",
            trigger:  ".s_website_form[data-model_name]",
        },
        {
            content:  "Click on Multiple Checkboxes in menu Add a custom field",
            trigger:  "we-button:contains('Multiple Checkboxes')",
        },

        // Customize custom multiple checkboxes field
        {
            content:  "Change the label",
            trigger:  ".col-form-label[for='Custom Multiple Checkboxes']",
            extra_trigger:  ".s_website_form:not(:has(.col-form-label[for='Custom Multiple Checkboxes']:eq(1)))",
            run:      "text Products"
        },
        {
            content:  "Change Option 1 label",
            trigger:  "label:contains('Option 1') span",
            run:      "text Iphone"
        },
        {
            content:  "Change Option 2 label",
            trigger:  "label:contains('Option 2') span",
            run:      "text Galaxy S"
        },
        {
            content:  "Click on Option 3",
            trigger:  "label:contains('Option 3') span",
        },
        {
            content:  "Duplicate Option 3",
            trigger:  ".oe_snippet_clone:last",
        },
        {
            content:  "Change first Option 3 label",
            trigger:  "label:contains('Option 3'):first span",
            run:      "text Xperia"
        },
        {
            content:  "Change last Option label",
            trigger:  "label:contains('Option 3') span",
            run:      "text Wiko Stairway"
        },
        {
            content:  "Click on field",
            trigger:  ".col-form-label:contains('Products')"
        },
        {
            content:  "Click on Required",
            trigger:  "[data-website_form_field_require]"
        },
        {
            content:  "Check the resulting field",
            trigger:  ".form-field.o_website_form_custom.o_website_form_required_custom" +
                            ":has(.col-form-label:contains('Products'))" +
                            ":has(.checkbox label:contains('Iphone'):has(input[type='checkbox'][required]))" +
                            ":has(.checkbox label:contains('Galaxy S'):has(input[type='checkbox'][required]))" +
                            ":has(.checkbox label:contains('Xperia'):has(input[type='checkbox'][required]))" +
                            ":has(.checkbox label:contains('Wiko Stairway'):has(input[type='checkbox'][required]))",
            run:      function () {},
        },

        // Add a custom radio field
        {
            content:  "Click on Form snippet",
            trigger:  ".s_website_form[data-model_name]",
        },
        {
            content:  "Click on Radio Buttons in menu Add a custom field",
            trigger:  "we-button:contains('Radio Buttons')"
        },

        // Customize Radio Buttons field
        {
            content:  "Change the label",
            trigger:  ".col-form-label[for='Custom Radio Buttons']",
            run:      "text Service"
        },
        {
            content:  "Change Option 1 label",
            trigger:  "label:contains('Option 1') span",
            run:      "text After-sales Service"
        },
        {
            content:  "Change Option 2 label",
            trigger:  "label:contains('Option 2') span",
            run:      "text Invoicing Service"
        },
        {
            content:  "Click on Option 3",
            trigger:  "label:contains('Option 3') span",
        },
        {
            content:  "Duplicate Option 3",
            trigger:  ".oe_snippet_clone:last",
        },
        {
            content:  "Change first Option 3 label",
            trigger:  "label:contains('Option 3'):first span",
            run:      "text Development Service"
        },
        {
            content:  "Change last Option label",
            trigger:  "label:contains('Option 3') span",
            run:      "text Management Service"
        },
        {
            content:  "Click on field",
            trigger:  ".col-form-label:contains('Service')"
        },
        {
            content:  "Click on Required",
            trigger:  "[data-website_form_field_require]"
        },
        {
            content:  "Click on Required",
            trigger:  "[data-website_form_field_require]",
            extra_trigger:  ".form-field.o_website_form_custom.o_website_form_required_custom" +
                            ":has(.col-form-label:contains('Service'))",
        },
        {
            content:  "Check the resulting field",
            trigger:  ".form-field.o_website_form_custom:not(.o_website_form_required_custom)" +
                            ":has(.col-form-label:contains('Service'))" +
                            ":has(.radio label:contains('After-sales Service'):has(input[type='radio']:not([required])))" +
                            ":has(.radio label:contains('Invoicing Service'):has(input[type='radio']:not([required])))" +
                            ":has(.radio label:contains('Development Service'):has(input[type='radio']:not([required])))" +
                            ":has(.radio label:contains('Management Service'):has(input[type='radio']:not([required])))",
            run:      function () {},
        },


        // Add a custom selection field
        {
            content:  "Click on Form snippet",
            trigger:  ".s_website_form[data-model_name]",
        },
        {
            content:  "Click on Selection in menu Add a custom field",
            trigger:  "we-button:contains('Selection')",
        },

        // Customize custom selection field
        {
            content:  "Change the label",
            trigger:  ".col-form-label[for='Custom Selection']",
            run:      "text State"
        },
        {
            content:  "Change Option 1 Label",
            trigger:  ".o_website_form_select_item:contains('Option 1')",
            run:      "text Germany"
        },
        {
            content:  "Change Option 2 Label",
            trigger:  ".o_website_form_select_item:contains('Option 2')",
            run:      "text Belgium"
        },
        {
            content:  "Click on Option 3",
            trigger:  ".o_website_form_select_item:contains('Option 3')",
        },
        {
            content:  "Duplicate Option 3",
            trigger:  ".oe_snippet_clone:last",
        },
        {
            content:  "Change first Option 3 label",
            trigger:  ".o_website_form_select_item:contains('Option 3'):first",
            run:      "text France"
        },
        {
            content:  "Change last Option label",
            trigger:  ".o_website_form_select_item:contains('Option 3')",
            run:      "text Canada"
        },
        {
            content:  "Click on Germany Option",
            trigger:  ".o_website_form_select_item:contains('Germany')",
        },
        {
            content:  "Remove Germany Option",
            trigger:  ".oe_snippet_remove:last",
        },
        {
            content:  "Click on field",
            trigger:  ".col-form-label:contains('State')"
        },
        {
            content:  "Click on Required",
            trigger:  "[data-website_form_field_require]"
        },
        {
            content:  "Check the resulting snippet",
            trigger:  ".form-field.o_website_form_custom.o_website_form_required_custom" +
                            ":has(label:contains('State'))" +
                            ":has(select[required]:hidden)" +
                            ":has(.o_website_form_select_item:contains('Belgium'))" +
                            ":has(.o_website_form_select_item:contains('France'))" +
                            ":has(.o_website_form_select_item:contains('Canada'))" +
                            ":not(:has(.o_website_form_select_item:contains('Germany')))",
            run:      function () {},
        },

        // Add attachment_ids field
        {
            content:  "Click on Form snippet",
            trigger:  ".s_website_form[data-model_name]"
        },
        {
            content:  "Click on Add a model field",
            trigger:  "[data-website_form_field_modal]"
        },
        {
            content:  "Select the attachment_ids field",
            trigger:  "select[name='field_selection']",
            run:      "text attachment_ids"
        },
        {
            content:  "Click on Save",
            trigger:  ".modal-footer button:first"
        },

        // Customize attachment_ids field
        {
            content:  "Change the label",
            trigger:  ".col-form-label[for='attachment_ids']",
            run:      "text Invoice Scan"
        },
        {
            content:  "Check the resulting field",
            trigger:  ".form-field" +
                            ":has(input[type=file][name=attachment_ids])" +
                            ":has(label:contains('Invoice Scan'))",
            run:      function () {
                $('body').append('<div id="completlyloaded"></div>');
            },
        },

        // Save the page
        {
            content:  "Save the page",
            trigger:  "button[data-action=save]",
        },
        {
            content:  "Wait reloading...",
            trigger:  "html:not(:has(#completlyloaded)) div",
        }
    ]);

    tour.register("website_form_editor_tour_submit", {
        test: true,
    },[
        {
            content:  "Try to send empty form",
            extra_trigger:  "form[data-model_name='mail.mail']" +
                            "[data-success_page='/contactus-thank-you']" +
                            ":has(.form-field:has(label:contains('Your Name')):has(input[type='text'][name='Your Name'][required]))" +
                            ":has(.form-field:has(label:contains('Email')):has(input[type='email'][name='email_from'][required]))" +
                            ":has(.form-field:has(label:contains('Your Question')):has(textarea[name='Your Question'][required]))" +
                            ":has(.form-field:has(label:contains('Subject')):has(input[type='text'][name='subject'][required]))" +
                            ":has(.form-field:has(label:contains('Test Date')):has(input[type='text'][name='date'][required]))" +
                            ":has(.form-field:has(label:contains('Awesome Label')):hidden)" +
                            ":has(.form-field:has(label:contains('Your Message')):has(textarea[name='body_html'][required]))" +
                            ":has(.form-field:has(label:contains('Products')):has(input[type='checkbox'][name='Products'][value='Iphone'][required]))" +
                            ":has(.form-field:has(label:contains('Products')):has(input[type='checkbox'][name='Products'][value='Galaxy S'][required]))" +
                            ":has(.form-field:has(label:contains('Products')):has(input[type='checkbox'][name='Products'][value='Xperia'][required]))" +
                            ":has(.form-field:has(label:contains('Products')):has(input[type='checkbox'][name='Products'][value='Wiko Stairway'][required]))" +
                            ":has(.form-field:has(label:contains('Service')):has(input[type='radio'][name='Service'][value='After-sales Service']:not([required])))" +
                            ":has(.form-field:has(label:contains('Service')):has(input[type='radio'][name='Service'][value='Invoicing Service']:not([required])))" +
                            ":has(.form-field:has(label:contains('Service')):has(input[type='radio'][name='Service'][value='Development Service']:not([required])))" +
                            ":has(.form-field:has(label:contains('Service')):has(input[type='radio'][name='Service'][value='Management Service']:not([required])))" +
                            ":has(.form-field:has(label:contains('State')):has(select[name='State'][required]:has(option[value='Belgium'])))" +
                            ":has(.form-field.o_website_form_required_custom:has(label:contains('State')):has(select[name='State'][required]:has(option[value='France'])))" +
                            ":has(.form-field:has(label:contains('State')):has(select[name='State'][required]:has(option[value='Canada'])))" +
                            ":has(.form-field:has(label:contains('Invoice Scan')))" +
                            ":has(.form-field:has(input[name='email_to'][value='test@test.test']))",
            trigger:  ".o_website_form_send"
        },
        {
            content:  "Check if required fields were detected and complete the Subject field",
            extra_trigger:  "form:has(#o_website_form_result.text-danger)" +
                            ":has(.form-field:has(label:contains('Your Name')).o_has_error)" +
                            ":has(.form-field:has(label:contains('Email')).o_has_error)" +
                            ":has(.form-field:has(label:contains('Your Question')).o_has_error)" +
                            ":has(.form-field:has(label:contains('Subject')).o_has_error)" +
                            ":has(.form-field:has(label:contains('Test Date')).o_has_error)" +
                            ":has(.form-field:has(label:contains('Your Message')).o_has_error)" +
                            ":has(.form-field:has(label:contains('Products')).o_has_error)" +
                            ":has(.form-field:has(label:contains('Service')):not(.o_has_error))" +
                            ":has(.form-field:has(label:contains('State')):not(.o_has_error))" +
                            ":has(.form-field:has(label:contains('Invoice Scan')):not(.o_has_error))",
            trigger:  "input[name=subject]",
            run:      "text Jane Smith"
        },
        {
            content:  "Update required field status by trying to Send again",
            trigger:  ".o_website_form_send"
        },
        {
            content:  "Check if required fields were detected and complete the Message field",
            extra_trigger:  "form:has(#o_website_form_result.text-danger)" +
                            ":has(.form-field:has(label:contains('Your Name')).o_has_error)" +
                            ":has(.form-field:has(label:contains('Email')).o_has_error)" +
                            ":has(.form-field:has(label:contains('Your Question')).o_has_error)" +
                            ":has(.form-field:has(label:contains('Subject')):not(.o_has_error))" +
                            ":has(.form-field:has(label:contains('Test Date')).o_has_error)" +
                            ":has(.form-field:has(label:contains('Your Message')).o_has_error)" +
                            ":has(.form-field:has(label:contains('Products')).o_has_error)" +
                            ":has(.form-field:has(label:contains('Service')):not(.o_has_error))" +
                            ":has(.form-field:has(label:contains('State')):not(.o_has_error))" +
                            ":has(.form-field:has(label:contains('Invoice Scan')):not(.o_has_error))",
            trigger:  "textarea[name=body_html]",
            run:      "text A useless message"
        },
        {
            content:  "Update required field status by trying to Send again",
            trigger:  ".o_website_form_send"
        },
        {
            content:  "Check if required fields was detected and check a product. If this fails, you probably broke the cleanForSave.",
            extra_trigger:  "form:has(#o_website_form_result.text-danger)" +
                            ":has(.form-field:has(label:contains('Your Name')).o_has_error)" +
                            ":has(.form-field:has(label:contains('Email')).o_has_error)" +
                            ":has(.form-field:has(label:contains('Your Question')).o_has_error)" +
                            ":has(.form-field:has(label:contains('Subject')):not(.o_has_error))" +
                            ":has(.form-field:has(label:contains('Test Date')).o_has_error)" +
                            ":has(.form-field:has(label:contains('Your Message')):not(.o_has_error))" +
                            ":has(.form-field:has(label:contains('Products')).o_has_error)" +
                            ":has(.form-field:has(label:contains('Service')):not(.o_has_error))" +
                            ":has(.form-field:has(label:contains('State')):not(.o_has_error))" +
                            ":has(.form-field:has(label:contains('Invoice Scan')):not(.o_has_error))",
            trigger:  "input[name=Products][value='Wiko Stairway']"
        },
        {
            content:  "Complete Date field",
            trigger:  ".o_website_form_datetime [data-toggle='datetimepicker']",
        },
        {
            content:  "Check another product",
            trigger:  "input[name='Products'][value='Xperia']"
        },
        {
            content:  "Check a service",
            trigger:  "input[name='Service'][value='Development Service']"
        },
        {
            content:  "Complete Your Name field",
            trigger:  "input[name='Your Name']",
            run:      "text chhagan"
        },
        {
            content:  "Complete Email field",
            trigger:  "input[name=email_from]",
            run:      "text test@mail.com"
        },
        {
            content:  "Complete Your Question field",
            trigger:  "textarea[name='Your Question']",
            run:      "text magan"
        },
        {
            content:  "Send the form",
            trigger:  ".o_website_form_send"
        },
        {
            content:  "Check form is submitted without errors",
            trigger:  ".alert-success:contains('Your message has been sent successfully.')"
        }
    ]);

    tour.register("website_form_editor_tour_results", {
        test: true,
    }, [
        {
            content: "Check mail.mail records have been created",
            trigger: "body",
            run: function () {
                var mailDef = rpc.query({
                        model: 'mail.mail',
                        method: 'search_count',
                        args: [[
                            ['email_to', '=', 'test@test.test'],
                            ['body_html', 'like', 'A useless message'],
                            ['body_html', 'like', 'Service : Development Service'],
                            ['body_html', 'like', 'State : Belgium'],
                            ['body_html', 'like', 'Products : Xperia,Wiko Stairway']
                        ]],
                    });
                var success = function(model, count) {
                    if (count > 0) {
                        $('body').append('<div id="website_form_editor_success_test_tour_'+model+'"></div>');
                    }
                };
                mailDef.then(_.bind(success, this, 'mail_mail'));
            }
        },
        {
            content:  "Check mail.mail records have been created",
            trigger:  "#website_form_editor_success_test_tour_mail_mail"
        }
    ]);

    return {};
});
