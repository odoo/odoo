odoo.define('website_form_editor.tour', function(require) {
    'use strict';

    var base = require('web_editor.base');
    var core    = require('web.core');
    var Tour    = require('web.Tour');
    var Model   = require('web.Model');
    var Session = require('web.Session');

    base.ready().done(function () {
        Tour.register({
            id:   'website_form_editor_tour',
            name: "Try to create some forms",
            path: '/',
            mode: 'test',
            steps: [
                // Drop a form builder snippet and configure it
                {
                    title:          "Enter edit mode",
                    element:        "button[data-action=edit]"
                },
                {
                    title:          "Drop the form snippet",
                    snippet:        "#snippet_feature .oe_snippet[name='Form Builder']"
                },
                {
                    title:          "Check if the snippet is dropped and if the modal is opened",
                    waitFor:        "body:has(form[action*='/website_form/'])" +
                                    ":has(.modal-body:has(select[name='model_selection'])" +
                                    ":has(input[name='success_page']))"
                },
                {
                    title:          "Change the action to create issues",
                    element:        ".modal-body select",
                    sampleText:     "project.issue"

                },
                {
                    title:          "Change the action to Send an E-mail",
                    // waitFor:        ".modal-body .o_form-action-mailto:hidden",
                    element:        ".modal-body select",
                    sampleText:     "mail.mail"
                },
                {
                    title:          "Complete Recipient E-mail",
                    waitFor:        ".modal-body input[name='email_to']",
                    element:        ".modal-body input[name='email_to']",
                    sampleText:     "test@test.test"
                },
                {
                    title:          "Click on Save",
                    element:        ".modal-footer #modal-save"
                },
                // Add the subject field
                {
                    title:          "Click on Form snippet",
                    element:        ".s_website_form[data-model_name]"
                },
                {
                    title:          "Click on Customize",
                    element:        ".oe_overlay_options:visible a[title='Customize']"
                },
                {
                    title:          "Click on Add a model field",
                    element:        ".oe_overlay_options:visible li[data-website_form_field_modal] a"
                },
                {
                    title:          "Select the subject field",
                    element:        "select[name='field_selection']",
                    sampleText:     "subject"
                },
                {
                    title:          "Click on Save",
                    element:        ".modal-footer #modal-save"
                },

                // Customize subject field
                {
                    title:          "Change the label",
                    element:        ".control-label[for='subject']",
                    sampleText:     "Name"
                },
                {
                    title:          "Click on Customize",
                    element:        ".oe_overlay_options:visible a[title='Customize']"
                },
                {
                    title:          "Click on Required",
                    element:        ".oe_overlay_options:visible li[data-website_form_field_require] a"
                },
                {
                    title:          "Check the resulting field",
                    waitFor:        ".form-field.o_website_form_required_custom" +
                                    ":has(input[type=text][name=subject][required])" +
                                    ":has(label:contains('Name'))"
                },

                // Add record_name field
                {
                    title:          "Click on Form snippet",
                    element:        ".s_website_form[data-model_name]"
                },
                {
                    title:          "Click on Customize",
                    element:        ".oe_overlay_options:visible a[title='Customize']"
                },
                {
                    title:          "Click on Add a model field",
                    element:        ".oe_overlay_options:visible li[data-website_form_field_modal] a"
                },
                {
                    title:          "Select the record_name field",
                    element:        "select[name='field_selection']",
                    sampleText:     "record_name"
                },
                {
                    title:          "Click on Save",
                    element:        ".modal-footer #modal-save"
                },

                // Customize record_name field
                {
                    title:          "Change the label",
                    element:        ".control-label[for='record_name']",
                    sampleText:     "Awesome Label"
                },
                {
                    title:          "Click on Customize",
                    element:        ".oe_overlay_options:visible a[title='Customize']"
                },
                {
                    title:          "Click on Hidden",
                    element:        ".oe_overlay_options:visible li[data-toggle_class='o_website_form_field_hidden'] a"
                },
                {
                    title:          "Check the resulting field",
                    waitFor:        ".form-field.o_website_form_field_hidden" +
                                    ":has(input:not([required])[type=text][name=record_name])" +
                                    ":has(label:contains('Awesome Label'))"
                },


                // Add body_html field
                {
                    title:          "Click on Form snippet",
                    element:        ".s_website_form[data-model_name]"
                },
                {
                    title:          "Click on Customize",
                    element:        ".oe_overlay_options:visible a[title='Customize']"
                },
                {
                    title:          "Click on Add a model field",
                    element:        ".oe_overlay_options:visible li[data-website_form_field_modal] a"
                },
                {
                    title:          "Select the body_html field",
                    element:        "select[name='field_selection']",
                    sampleText:     "body_html"
                },
                {
                    title:          "Click on Save",
                    element:        ".modal-footer #modal-save"
                },

                // Customize subject field
                {
                    title:          "Change the label",
                    element:        ".control-label[for='body_html']",
                    sampleText:     "Your Message"
                },
                {
                    title:          "Click on Customize",
                    element:        ".oe_overlay_options:visible a[title='Customize']"
                },
                {
                    title:          "Click on Required",
                    element:        ".oe_overlay_options:visible li[data-website_form_field_require] a"
                },
                {
                    title:          "Check the resulting field",
                    waitFor:        ".form-field.o_website_form_required_custom" +
                                    ":has(textarea[name=body_html][required])" +
                                    ":has(label:contains('Your Message'))"
                },

                // Add recipient_ids relational field
                {
                    title:          "Click on Form snippet",
                    element:        ".s_website_form[data-model_name]"
                },
                {
                    title:          "Click on Customize",
                    element:        ".oe_overlay_options:visible a[title='Customize']"
                },
                {
                    title:          "Click on Add a model field",
                    element:        ".oe_overlay_options:visible li[data-website_form_field_modal] a"
                },
                {
                    title:          "Select the recipient_ids field",
                    element:        "select[name='field_selection']",
                    sampleText:     "recipient_ids"
                },
                {
                    title:          "Click on Save",
                    element:        ".modal-footer #modal-save"
                },
                {
                    title:          "Check the resulting field",
                    waitFor:        ".form-field:has(.control-label:contains('To (Partners)'))"
                },

                // Add a custom multiple checkboxes field
                {
                    title:          "Click on Form snippet",
                    element:        ".s_website_form[data-model_name]",
                    onend: function() {
                        // I didn't find any other way to make that submenu element appear
                        $(".oe_options > ul > li:has(ul) > ul").css("display", "block");
                    }
                },
                {
                    title:          "Click on Customize",
                    element:        ".oe_overlay_options:visible a[title='Customize']"
                },
                {
                    title:          "Click on Multiple Checkboxes in menu Add a custom field",
                    element:        ".oe_options li a:contains('Multiple Checkboxes')"
                },

                // Customize custom multiple checkboxes field
                {
                    title:          "Change the label",
                    element:        ".control-label[for='Custom Multiple Checkboxes']",
                    sampleText:     "Products"
                },
                {
                    title:          "Change Option 1 label",
                    element:        "label:contains('Option 1') span",
                    sampleText:     "Iphone"
                },
                {
                    title:          "Change Option 2 label",
                    element:        "label:contains('Option 2') span",
                    sampleText:     "Galaxy S"
                },
                {
                    title:          "Click on Option 3",
                    element:        "label:contains('Option 3') span",
                },
                {
                    title:          "Duplicate Option 3",
                    element:        ".oe_overlay_options:visible .oe_snippet_clone",
                },
                {
                    title:          "Change first Option 3 label",
                    element:        "label:contains('Option 3'):first span",
                    sampleText:     "Xperia"
                },
                {
                    title:          "Change last Option label",
                    element:        "label:contains('Option 3') span",
                    sampleText:     "Wiko Stairway"
                },
                {
                    title:          "Click on field",
                    element:        ".control-label:contains('Products')"
                },
                {
                    title:          "Click on Customize",
                    element:        ".oe_overlay_options:visible a[title='Customize']"
                },
                {
                    title:          "Click on Required",
                    element:        ".oe_overlay_options:visible li[data-website_form_field_require] a"
                },
                {
                    title:          "Check the resulting field",
                    waitFor:        ".form-field.o_website_form_custom.o_website_form_required_custom" +
                                    ":has(.control-label:contains('Products'))" +
                                    ":has(.checkbox label:contains('Iphone'):has(input[type='checkbox'][required]))" +
                                    ":has(.checkbox label:contains('Galaxy S'):has(input[type='checkbox'][required]))" +
                                    ":has(.checkbox label:contains('Xperia'):has(input[type='checkbox'][required]))" +
                                    ":has(.checkbox label:contains('Wiko Stairway'):has(input[type='checkbox'][required]))"
                },

                // Add a custom radio field
                {
                    title:          "Click on Form snippet",
                    element:        ".s_website_form[data-model_name]",
                },
                {
                    title:          "Click on Customize",
                    element:        ".oe_overlay_options:visible a[title='Customize']"
                },
                {
                    title:          "Click on Radio Buttons in menu Add a custom field",
                    element:        ".oe_options li a:contains('Radio Buttons')"
                },

                // Customize custom multiple checkboxes field
                {
                    title:          "Change the label",
                    element:        ".control-label[for='Custom Radio Buttons']",
                    sampleText:     "Service"
                },
                {
                    title:          "Change Option 1 label",
                    element:        "label:contains('Option 1') span",
                    sampleText:     "After-sales Service"
                },
                {
                    title:          "Change Option 2 label",
                    element:        "label:contains('Option 2') span",
                    sampleText:     "Invoicing Service"
                },
                {
                    title:          "Click on Option 3",
                    element:        "label:contains('Option 3') span",
                },
                {
                    title:          "Duplicate Option 3",
                    element:        ".oe_overlay_options:visible .oe_snippet_clone",
                },
                {
                    title:          "Change first Option 3 label",
                    element:        "label:contains('Option 3'):first span",
                    sampleText:     "Development Service"
                },
                {
                    title:          "Change last Option label",
                    element:        "label:contains('Option 3') span",
                    sampleText:     "Management Service"
                },
                {
                    title:          "Click on field",
                    element:        ".control-label:contains('Service')"
                },
                {
                    title:          "Click on Customize",
                    element:        ".oe_overlay_options:visible a[title='Customize']"
                },
                {
                    title:          "Click on Required",
                    element:        ".oe_overlay_options:visible li[data-website_form_field_require] a"
                },
                {
                    title:          "Click on Customize",
                    element:        ".oe_overlay_options:visible a[title='Customize']"
                },
                {
                    title:          "Click on Required",
                    element:        ".oe_overlay_options:visible li[data-website_form_field_require] a"
                },
                {
                    title:          "Check the resulting field",
                    waitFor:        ".form-field.o_website_form_custom:not(.o_website_form_required_custom)" +
                                    ":has(.control-label:contains('Service'))" +
                                    ":has(.radio label:contains('After-sales Service'):has(input[type='radio']:not([required])))" +
                                    ":has(.radio label:contains('Invoicing Service'):has(input[type='radio']:not([required])))" +
                                    ":has(.radio label:contains('Development Service'):has(input[type='radio']:not([required])))" +
                                    ":has(.radio label:contains('Management Service'):has(input[type='radio']:not([required])))"
                },


                // Add a custom selection field
                {
                    title:          "Click on Form snippet",
                    element:        ".s_website_form[data-model_name]",
                    onend: function() {
                        // I didn't find any other way to make that submenu element appear
                        $(".oe_options > ul > li:has(ul) > ul").css("display", "block");
                    }
                },
                {
                    title:          "Click on Customize",
                    element:        ".oe_overlay_options:visible a[title='Customize']"
                },
                {
                    title:          "Click on Selection in menu Add a custom field",
                    element:        ".oe_options li a:contains('Selection')"
                },

                // Customize custom selection field
                {
                    title:          "Change the label",
                    element:        ".control-label[for='Custom Selection']",
                    sampleText:     "State"
                },
                {
                    title:          "Change Option 1 Label",
                    element:        ".o_website_form_select_item:contains('Option 1')",
                    sampleText:     "Germany"
                },
                {
                    title:          "Change Option 2 Label",
                    element:        ".o_website_form_select_item:contains('Option 2')",
                    sampleText:     "Belgium"
                },
                {
                    title:          "Click on Option 3",
                    element:        ".o_website_form_select_item:contains('Option 3')",
                },
                {
                    title:          "Duplicate Option 3",
                    element:        ".oe_overlay_options:visible .oe_snippet_clone",
                },
                {
                    title:          "Change first Option 3 label",
                    element:        ".o_website_form_select_item:contains('Option 3'):first",
                    sampleText:     "France"
                },
                {
                    title:          "Change last Option label",
                    element:        ".o_website_form_select_item:contains('Option 3')",
                    sampleText:     "Canada"
                },
                {
                    title:          "Click on Germany Option",
                    element:        ".o_website_form_select_item:contains('Germany')",
                },
                {
                    title:          "Remove Germany Option",
                    element:        ".oe_overlay_options:visible .oe_snippet_remove",
                },
                {
                    title:          "Click on field",
                    element:        ".control-label:contains('State')"
                },
                {
                    title:          "Click on Customize",
                    element:        ".oe_overlay_options:visible a[title='Customize']"
                },
                {
                    title:          "Click on Required",
                    element:        ".oe_overlay_options:visible li[data-website_form_field_require] a"
                },
                {
                    title:          "Check the resulting snippet",
                    waitFor:        ".form-field.o_website_form_custom.o_website_form_required_custom" +
                                    ":has(label:contains('State'))" +
                                    ":has(select[required]:hidden)" +
                                    ":has(.o_website_form_select_item:contains('Belgium'))" +
                                    ":has(.o_website_form_select_item:contains('France'))" +
                                    ":has(.o_website_form_select_item:contains('Canada'))" +
                                    ":not(:has(.o_website_form_select_item:contains('Germany')))"
                },

                // Add attachment_ids field
                {
                    title:          "Click on Form snippet",
                    element:        ".s_website_form[data-model_name]"
                },
                {
                    title:          "Click on Customize",
                    element:        ".oe_overlay_options:visible a[title='Customize']"
                },
                {
                    title:          "Click on Add a model field",
                    element:        ".oe_overlay_options:visible li[data-website_form_field_modal] a"
                },
                {
                    title:          "Select the attachment_ids field",
                    element:        "select[name='field_selection']",
                    sampleText:     "attachment_ids"
                },
                {
                    title:          "Click on Save",
                    element:        ".modal-footer #modal-save"
                },

                // Customize attachment_ids field
                {
                    title:          "Change the label",
                    element:        ".control-label[for='attachment_ids']",
                    sampleText:     "Invoice Scan"
                },
                {
                    title:          "Check the resulting field",
                    waitFor:        ".form-field" +
                                    ":has(input[type=file][name=attachment_ids])" +
                                    ":has(label:contains('Invoice Scan'))"
                },

                // Save the page
                {
                    title:          "Save the page",
                    element:        "button[data-action=save]",
                    onload: function (tour) {
                        setTimeout(function(){
                            $('html').append('<div id="completlyloaded"></div>');
                        }, 1000);
                    }
                },
                {
                    title:          "Wait reloading...",
                    waitFor:        "#completlyloaded",
                    onload: function (tour) {
                        $("#completlyloaded").remove();
                    }
                }
            ]
        });

        Tour.register({
            id:   'website_form_editor_tour_submit',
            name: "Check created form works correctly",
            path: '',
            mode: 'test',
            steps: [
                {
                    title:          "Try to send empty form",
                    waitFor:        "form[data-model_name='mail.mail']" +
                                    "[data-success_page='']" +
                                    ":has(.form-field:has(label:contains('Name')):has(input[type='text'][name='subject'][required]))" +
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
                                    ":has(input.form-field[name='email_to'][value='test@test.test'])",
                    element:        ".o_website_form_send"
                },
                {
                    title:          "Check if required fields were detected and complete the Name field",
                    waitFor:        "form:has(#o_website_form_result.text-danger)" +
                                    ":has(.form-field:has(label:contains('Name')).has-error)" +
                                    ":has(.form-field:has(label:contains('Your Message')).has-error)" +
                                    ":has(.form-field:has(label:contains('Products')).has-error)" +
                                    ":has(.form-field:has(label:contains('Service')):not(.has-error))" +
                                    ":has(.form-field:has(label:contains('State')):not(.has-error))" +
                                    ":has(.form-field:has(label:contains('Invoice Scan')):not(.has-error))",
                    element:        "input[name=subject]",
                    sampleText:     "Jane Smith"
                },
                {
                    title:          "Update required field status by trying to Send again",
                    element:        ".o_website_form_send"
                },
                {
                    title:          "Check if required fields were detected and complete the Message field",
                    waitFor:        "form:has(#o_website_form_result.text-danger)" +
                                    ":has(.form-field:has(label:contains('Name')):not(.has-error))" +
                                    ":has(.form-field:has(label:contains('Your Message')).has-error)" +
                                    ":has(.form-field:has(label:contains('Products')).has-error)" +
                                    ":has(.form-field:has(label:contains('Service')):not(.has-error))" +
                                    ":has(.form-field:has(label:contains('State')):not(.has-error))" +
                                    ":has(.form-field:has(label:contains('Invoice Scan')):not(.has-error))",
                    element:        "textarea[name=body_html]",
                    sampleText:     "A useless message"
                },
                {
                    title:          "Update required field status by trying to Send again",
                    element:        ".o_website_form_send"
                },
                {
                    title:          "Check if required fields was detected and check a product. If this fails, you probably broke the clean_for_save.",
                    waitFor:        "form:has(#o_website_form_result.text-danger)" +
                                    ":has(.form-field:has(label:contains('Name')):not(.has-error))" +
                                    ":has(.form-field:has(label:contains('Your Message')):not(.has-error))" +
                                    ":has(.form-field:has(label:contains('Products')).has-error)" +
                                    ":has(.form-field:has(label:contains('Service')):not(.has-error))" +
                                    ":has(.form-field:has(label:contains('State')):not(.has-error))" +
                                    ":has(.form-field:has(label:contains('Invoice Scan')):not(.has-error))",
                    element:        "input[name=Products][value='Wiko Stairway']"
                },
                {
                    title:          "Check another product",
                    element:        "input[name='Products'][value='Xperia']"
                },
                {
                    title:          "Check a service",
                    element:        "input[name='Service'][value='Development Service']"
                },
                {
                    title:          "Send the form",
                    element:        ".o_website_form_send"
                },
                {
                    title:          "Check form is submitted without errors",
                    waitFor:        "form:has(#o_website_form_result.text-success)" +
                                    ":has(.form-field:has(label:contains('Name')):not(.has-error))" +
                                    ":has(.form-field:has(label:contains('Your Message')):not(.has-error))" +
                                    ":has(.form-field:has(label:contains('Products')):not(.has-error))" +
                                    ":has(.form-field:has(label:contains('Service')):not(.has-error))" +
                                    ":has(.form-field:has(label:contains('State')):not(.has-error))" +
                                    ":has(.form-field:has(label:contains('Invoice Scan')):not(.has-error))"
                }
            ]
        });

        Tour.register({
            id:   'website_form_editor_tour_results',
            name: "Check records have been created",
            path: '',
            mode: 'test',
            steps: [
                {
                    title:          "Check mail.mail records have been created",
                    waitFor:        ".o-apps",
                    onload: function (tour) {
                        var mailDef = new Model("mail.mail").call(
                            "search_read",
                            [
                                // TODO: add other fields in domain !
                                [
                                    ['email_to', '=', 'test@test.test'],
                                    ['body_html', 'like', 'A useless message'],
                                    ['body_html', 'like', 'Service : Development Service'],
                                    ['body_html', 'like', 'State : Belgium'],
                                    ['body_html', 'like', 'Products : Xperia,Wiko Stairway']
                                ],
                                []
                            ]
                        );
                        var success = function(model, data) {
                            if(data.length) {
                                $('body').append('<div id="website_form_editor_success_test_tour_'+model+'"></div>');
                            }
                        };
                        mailDef.then(_.bind(success, this, 'mail_mail'));
                    }
                },
                {
                    title:          "Check mail.mail records have been created",
                    waitFor:        "#website_form_editor_success_test_tour_mail_mail"
                },
                {
                    title:          "Final Step",
                    waitFor:        "html"
                }
            ]
        });
    });

    return {};
});
