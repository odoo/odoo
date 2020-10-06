odoo.define('website_form_editor.tour', function (require) {
    'use strict';

    const rpc = require('web.rpc');
    const tour = require("web_tour.tour");

    const selectButtonByText = function (text) {
        return [{
            content: "Open the select",
            trigger: `we-select:has(we-button:contains("${text}")) we-toggler`,
        },
        {
            content: "Click on the option",
            trigger: `we-select we-button:contains("${text}")`,
        }];
    };
    const selectButtonByData = function (data) {
        return [{
            content: "Open the select",
            trigger: `we-select:has(we-button[${data}]) we-toggler`,
        }, {
            content: "Click on the option",
            trigger: `we-select we-button[${data}]`,
        }];
    };
    const addField = function (data, name, type, label, required, hidden) {
        const ret = [{
            content: "Select form",
            extra_trigger: '.s_website_form_field',
            trigger: 'section.s_website_form',
        }, {
            content: "Add field",
            trigger: 'we-button[data-add-field]',
        },
        ...selectButtonByData(data),
        {
            content: "Wait for field to load",
            trigger: `.s_website_form_field[data-type="${name}"], .s_website_form_input[name="${name}"]`, //custom or existing field
            run: function () {},
        }];
        let testText = '.s_website_form_field';
        if (required) {
            testText += '.s_website_form_required';
            ret.push({
                content: "Mark the field as required",
                trigger: 'we-button[data-name="required_opt"] we-checkbox',
            });
        }
        if (hidden) {
            testText += '.s_website_form_field_hidden';
            ret.push({
                content: "Mark the field as hidden",
                trigger: 'we-button[data-name="hidden_opt"] we-checkbox',
            });
        }
        if (label) {
            testText += `:has(label:contains("${label}"))`;
            ret.push({
                content: "Change the label text",
                trigger: 'we-input[data-set-label-text] input',
                run: `text ${label}`,
            });
        }
        if (type !== 'checkbox' && type !== 'radio' && type !== 'select') {
            let inputType = type === 'textarea' ? type : `input[type="${type}"]`;
            testText += `:has(${inputType}[name="${name}"]${required ? '[required]' : ''})`;
        }
        ret.push({
            content: "Check the resulting field",
            trigger: testText,
            run: function () {},
        });
        return ret;
    };
    const addCustomField = function (name, type, label, required, hidden) {
        return addField(`data-custom-field="${name}"`, name, type, label, required, hidden);
    };
    const addExistingField = function (name, type, label, required, hidden) {
        return addField(`data-existing-field="${name}"`, name, type, label, required, hidden);
    };

    tour.register("website_form_editor_tour", {
        test: true,
    }, [
        // Drop a form builder snippet and configure it
        {
            content: "Enter edit mode",
            trigger: 'a[data-action=edit]',
        }, {
            content: "Drop the form snippet",
            trigger: '#oe_snippets .oe_snippet:has(.s_website_form) .oe_snippet_thumbnail',
            run: 'drag_and_drop #wrap',
        }, {
            content: "Check dropped snippet and select it",
            extra_trigger: '.s_website_form_field',
            trigger: 'section.s_website_form',
        },
        ...selectButtonByText('Send an E-mail'),
        {
            content: "Form has a model name",
            trigger: 'section.s_website_form form[data-model_name="mail.mail"]',
        }, {
            content: "Complete Recipient E-mail",
            trigger: '[data-field-name="email_to"] input',
            run: 'text_blur test@test.test',
        },
        ...addExistingField('date', 'text', 'Test Date', true),

        ...addExistingField('record_name', 'text', 'Awesome Label', false, true),

        ...addExistingField('body_html', 'textarea', 'Your Message', true),

        ...addExistingField('recipient_ids', 'checkbox'),

        ...addCustomField('one2many', 'checkbox', 'Products', true),
        {
            content: "Change Option 1 label",
            trigger: 'we-list table input:eq(0)',
            run: 'text Iphone',
        }, {
            content: "Change Option 2 label",
            trigger: 'we-list table input:eq(1)',
            run: 'text Galaxy S',
        }, {
            content: "Change first Option 3 label",
            trigger: 'we-list table input:eq(2)',
            run: 'text Xperia',
        }, {
            content: "Click on Add new Checkbox",
            trigger: 'we-list we-button.o_we_list_add_optional',
        }, {
            content: "Change added Option label",
            trigger: 'we-list table input:eq(3)',
            run: 'text Wiko Stairway',
        }, {
            content: "Check the resulting field",
            trigger: ".s_website_form_field.s_website_form_custom.s_website_form_required" +
                        ":has(.s_website_form_multiple[data-display='horizontal'])" +
                        ":has(.checkbox:has(label:contains('Iphone')):has(input[type='checkbox'][required]))" +
                        ":has(.checkbox:has(label:contains('Galaxy S')):has(input[type='checkbox'][required]))" +
                        ":has(.checkbox:has(label:contains('Xperia')):has(input[type='checkbox'][required]))" +
                        ":has(.checkbox:has(label:contains('Wiko Stairway')):has(input[type='checkbox'][required]))",
            run: function () {},
        },
        ...selectButtonByData('data-multi-checkbox-display="vertical"'),
        {
            content: "Check the resulting field",
            trigger: ".s_website_form_field.s_website_form_custom.s_website_form_required" +
                        ":has(.s_website_form_multiple[data-display='vertical'])" +
                        ":has(.checkbox:has(label:contains('Iphone')):has(input[type='checkbox'][required]))" +
                        ":has(.checkbox:has(label:contains('Galaxy S')):has(input[type='checkbox'][required]))" +
                        ":has(.checkbox:has(label:contains('Xperia')):has(input[type='checkbox'][required]))" +
                        ":has(.checkbox:has(label:contains('Wiko Stairway')):has(input[type='checkbox'][required]))",
            run: function () {},
        },

        ...addCustomField('selection', 'radio', 'Service', true),
        {
            content: "Change Option 1 label",
            trigger: 'we-list table input:eq(0)',
            run: 'text After-sales Service',
        }, {
            content: "Change Option 2 label",
            trigger: 'we-list table input:eq(1)',
            run: 'text Invoicing Service',
        }, {
            content: "Change first Option 3 label",
            trigger: 'we-list table input:eq(2)',
            run: 'text Development Service',
        }, {
            content: "Click on Add new Checkbox",
            trigger: 'we-list we-button.o_we_list_add_optional',
        }, {
            content: "Change last Option label",
            trigger: 'we-list table input:eq(3)',
            run: 'text Management Service',
        }, {
            content: "Mark the field as not required",
            trigger: 'we-button[data-name="required_opt"] we-checkbox',
        }, {
            content: "Check the resulting field",
            trigger: ".s_website_form_field.s_website_form_custom:not(.s_website_form_required)" +
                        ":has(.radio:has(label:contains('After-sales Service')):has(input[type='radio']:not([required])))" +
                        ":has(.radio:has(label:contains('Invoicing Service')):has(input[type='radio']:not([required])))" +
                        ":has(.radio:has(label:contains('Development Service')):has(input[type='radio']:not([required])))" +
                        ":has(.radio:has(label:contains('Management Service')):has(input[type='radio']:not([required])))",
            run: function () {},
        },

        ...addCustomField('many2one', 'select', 'State', true),

        // Customize custom selection field
        {
            content: "Change Option 1 Label",
            trigger: 'we-list table input:eq(0)',
            run: 'text Germany',
        }, {
            content: "Change Option 2 Label",
            trigger: 'we-list table input:eq(1)',
            run: 'text Belgium',
        }, {
            content: "Change first Option 3 label",
            trigger: 'we-list table input:eq(2)',
            run: 'text France',
        }, {
            content: "Click on Add new Checkbox",
            trigger: 'we-list we-button.o_we_list_add_optional',
        }, {
            content: "Change last Option label",
            trigger: 'we-list table input:eq(3)',
            run: 'text Canada',
        }, {
            content: "Remove Germany Option",
            trigger: '.o_we_select_remove_option:eq(0)',
        }, {
            content: "Check the resulting snippet",
            trigger: ".s_website_form_field.s_website_form_custom.s_website_form_required" +
                        ":has(label:contains('State'))" +
                        ":has(select[required]:hidden)" +
                        ":has(.s_website_form_select_item:contains('Belgium'))" +
                        ":has(.s_website_form_select_item:contains('France'))" +
                        ":has(.s_website_form_select_item:contains('Canada'))" +
                        ":not(:has(.s_website_form_select_item:contains('Germany')))",
            run: function () {},
        },

        ...addExistingField('attachment_ids', 'file', 'Invoice Scan'),

        // Save the page
        {
            trigger: 'body',
            run: function () {
                $('body').append('<div id="completlyloaded"></div>');
            },
        },
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
                            "[data-success-page='/contactus-thank-you']" +
                            ":has(.s_website_form_field:has(label:contains('Your Name')):has(input[type='text'][name='Your Name'][required]))" +
                            ":has(.s_website_form_field:has(label:contains('Email')):has(input[type='email'][name='email_from'][required]))" +
                            ":has(.s_website_form_field:has(label:contains('Your Question')):has(textarea[name='Your Question'][required]))" +
                            ":has(.s_website_form_field:has(label:contains('Subject')):has(input[type='text'][name='subject'][required]))" +
                            ":has(.s_website_form_field:has(label:contains('Test Date')):has(input[type='text'][name='date'][required]))" +
                            ":has(.s_website_form_field:has(label:contains('Awesome Label')):hidden)" +
                            ":has(.s_website_form_field:has(label:contains('Your Message')):has(textarea[name='body_html'][required]))" +
                            ":has(.s_website_form_field:has(label:contains('Products')):has(input[type='checkbox'][name='Products'][value='Iphone'][required]))" +
                            ":has(.s_website_form_field:has(label:contains('Products')):has(input[type='checkbox'][name='Products'][value='Galaxy S'][required]))" +
                            ":has(.s_website_form_field:has(label:contains('Products')):has(input[type='checkbox'][name='Products'][value='Xperia'][required]))" +
                            ":has(.s_website_form_field:has(label:contains('Products')):has(input[type='checkbox'][name='Products'][value='Wiko Stairway'][required]))" +
                            ":has(.s_website_form_field:has(label:contains('Service')):has(input[type='radio'][name='Service'][value='After-sales Service']:not([required])))" +
                            ":has(.s_website_form_field:has(label:contains('Service')):has(input[type='radio'][name='Service'][value='Invoicing Service']:not([required])))" +
                            ":has(.s_website_form_field:has(label:contains('Service')):has(input[type='radio'][name='Service'][value='Development Service']:not([required])))" +
                            ":has(.s_website_form_field:has(label:contains('Service')):has(input[type='radio'][name='Service'][value='Management Service']:not([required])))" +
                            ":has(.s_website_form_field:has(label:contains('State')):has(select[name='State'][required]:has(option[value='Belgium'])))" +
                            ":has(.s_website_form_field.s_website_form_required:has(label:contains('State')):has(select[name='State'][required]:has(option[value='France'])))" +
                            ":has(.s_website_form_field:has(label:contains('State')):has(select[name='State'][required]:has(option[value='Canada'])))" +
                            ":has(.s_website_form_field:has(label:contains('Invoice Scan')))" +
                            ":has(.s_website_form_field:has(input[name='email_to'][value='test@test.test']))",
            trigger:  ".s_website_form_send"
        },
        {
            content:  "Check if required fields were detected and complete the Subject field",
            extra_trigger:  "form:has(#s_website_form_result.text-danger)" +
                            ":has(.s_website_form_field:has(label:contains('Your Name')).o_has_error)" +
                            ":has(.s_website_form_field:has(label:contains('Email')).o_has_error)" +
                            ":has(.s_website_form_field:has(label:contains('Your Question')).o_has_error)" +
                            ":has(.s_website_form_field:has(label:contains('Subject')).o_has_error)" +
                            ":has(.s_website_form_field:has(label:contains('Test Date')).o_has_error)" +
                            ":has(.s_website_form_field:has(label:contains('Your Message')).o_has_error)" +
                            ":has(.s_website_form_field:has(label:contains('Products')).o_has_error)" +
                            ":has(.s_website_form_field:has(label:contains('Service')):not(.o_has_error))" +
                            ":has(.s_website_form_field:has(label:contains('State')):not(.o_has_error))" +
                            ":has(.s_website_form_field:has(label:contains('Invoice Scan')):not(.o_has_error))",
            trigger:  "input[name=subject]",
            run:      "text Jane Smith"
        },
        {
            content:  "Update required field status by trying to Send again",
            trigger:  ".s_website_form_send"
        },
        {
            content:  "Check if required fields were detected and complete the Message field",
            extra_trigger:  "form:has(#s_website_form_result.text-danger)" +
                            ":has(.s_website_form_field:has(label:contains('Your Name')).o_has_error)" +
                            ":has(.s_website_form_field:has(label:contains('Email')).o_has_error)" +
                            ":has(.s_website_form_field:has(label:contains('Your Question')).o_has_error)" +
                            ":has(.s_website_form_field:has(label:contains('Subject')):not(.o_has_error))" +
                            ":has(.s_website_form_field:has(label:contains('Test Date')).o_has_error)" +
                            ":has(.s_website_form_field:has(label:contains('Your Message')).o_has_error)" +
                            ":has(.s_website_form_field:has(label:contains('Products')).o_has_error)" +
                            ":has(.s_website_form_field:has(label:contains('Service')):not(.o_has_error))" +
                            ":has(.s_website_form_field:has(label:contains('State')):not(.o_has_error))" +
                            ":has(.s_website_form_field:has(label:contains('Invoice Scan')):not(.o_has_error))",
            trigger:  "textarea[name=body_html]",
            run:      "text A useless message"
        },
        {
            content:  "Update required field status by trying to Send again",
            trigger:  ".s_website_form_send"
        },
        {
            content:  "Check if required fields was detected and check a product. If this fails, you probably broke the cleanForSave.",
            extra_trigger:  "form:has(#s_website_form_result.text-danger)" +
                            ":has(.s_website_form_field:has(label:contains('Your Name')).o_has_error)" +
                            ":has(.s_website_form_field:has(label:contains('Email')).o_has_error)" +
                            ":has(.s_website_form_field:has(label:contains('Your Question')).o_has_error)" +
                            ":has(.s_website_form_field:has(label:contains('Subject')):not(.o_has_error))" +
                            ":has(.s_website_form_field:has(label:contains('Test Date')).o_has_error)" +
                            ":has(.s_website_form_field:has(label:contains('Your Message')):not(.o_has_error))" +
                            ":has(.s_website_form_field:has(label:contains('Products')).o_has_error)" +
                            ":has(.s_website_form_field:has(label:contains('Service')):not(.o_has_error))" +
                            ":has(.s_website_form_field:has(label:contains('State')):not(.o_has_error))" +
                            ":has(.s_website_form_field:has(label:contains('Invoice Scan')):not(.o_has_error))",
            trigger:  "input[name=Products][value='Wiko Stairway']"
        },
        {
            content:  "Complete Date field",
            trigger:  ".s_website_form_datetime [data-toggle='datetimepicker']",
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
            content: "Complete Subject field",
            trigger: 'input[name="subject"]',
            run: 'text subject',
        },
        {
            content:  "Complete Your Question field",
            trigger:  "textarea[name='Your Question']",
            run:      "text magan"
        },
        {
            content:  "Send the form",
            trigger:  ".s_website_form_send"
        },
        {
            content:  "Check form is submitted without errors",
            trigger:  "#wrap:has(h1:contains('Thank You!'))"
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
