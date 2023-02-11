odoo.define('website.tour.form_editor', function (require) {
    'use strict';

    const rpc = require('web.rpc');
    const tour = require("web_tour.tour");

    // Visibility possible values:
    const VISIBLE = 'Always Visible';
    const HIDDEN = 'Hidden';
    const CONDITIONALVISIBILITY = 'Visible only if';

    const NB_NON_ESSENTIAL_REQUIRED_FIELDS_IN_DEFAULT_FORM = 2;
    const ESSENTIAL_FIELDS_VALID_DATA_FOR_DEFAULT_FORM = [
        {
            name: 'email_from',
            value: 'admin@odoo.com',
        },
        {
            name: 'subject',
            value: 'Hello, world!',
        }
    ];
    const essentialFieldsForDefaultFormFillInSteps = [];
    for (const data of ESSENTIAL_FIELDS_VALID_DATA_FOR_DEFAULT_FORM) {
        essentialFieldsForDefaultFormFillInSteps.push({
            content: "Enter data in model-required field",
            trigger: `.s_website_form_model_required .s_website_form_input[name="${data.name}"]`,
            run: `text ${data.value}`,
        });
    }

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
    const addField = function (data, name, type, label, required, display = {visibility: VISIBLE, condition: ''}) {
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
        },
        ...selectButtonByText(display.visibility),
    ];
        let testText = '.s_website_form_field';
        if (display.condition) {
            ret.push({
                content: "Set the visibility condition",
                trigger: 'we-input[data-attribute-name="visibilityCondition"] input',
                run: `text ${display.condition}`,
            });
        }
        if (required) {
            testText += '.s_website_form_required';
            ret.push({
                content: "Mark the field as required",
                trigger: 'we-button[data-name="required_opt"] we-checkbox',
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
    const addCustomField = function (name, type, label, required, display) {
        return addField(`data-custom-field="${name}"`, name, type, label, required, display);
    };
    const addExistingField = function (name, type, label, required, display) {
        return addField(`data-existing-field="${name}"`, name, type, label, required, display);
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
            content: "Select form by clicking on an input field",
            extra_trigger: '.s_website_form_field',
            trigger: 'section.s_website_form input',
        }, {
            content: "Verify that the form editor appeared",
            trigger: '.o_we_customize_panel .snippet-option-WebsiteFormEditor',
            run: () => null,
        }, {
            content: "Go back to blocks to unselect form",
            trigger: '.o_we_add_snippet_btn',
        }, {
            content: "Select form by clicking on a text area",
            extra_trigger: '.s_website_form_field',
            trigger: 'section.s_website_form textarea',
        }, {
            content: "Verify that the form editor appeared",
            trigger: '.o_we_customize_panel .snippet-option-WebsiteFormEditor',
            run: () => null,
        }, {
            content: "Rename the field label",
            trigger: 'we-input[data-set-label-text] input',
            run: "text Renamed",
        }, {
            content: "Leave the rename options",
            trigger: 'we-input[data-set-label-text] input',
            run: "text_blur",
        }, {
            content: "Go back to blocks to unselect form",
            trigger: '.o_we_add_snippet_btn',
        }, {
            content: "Select form itself (not a specific field)",
            extra_trigger: '.s_website_form_field',
            trigger: 'section.s_website_form',
        },
        ...selectButtonByText('Send an E-mail'),
        {
            content: "Form has a model name",
            trigger: 'section.s_website_form form[data-model_name="mail.mail"]',
        }, {
            content: 'Edit the Phone Number field',
            trigger: 'input[name="phone"]',
        }, {
            content: 'Change the label position of the phone field',
            trigger: 'we-button[data-select-label-position="right"]',
        },
        ...addExistingField('email_cc', 'text', 'Test conditional visibility', false, {visibility: CONDITIONALVISIBILITY, condition: 'odoo'}),

        ...addExistingField('date', 'text', 'Test Date', true),

        ...addExistingField('record_name', 'text', 'Awesome Label', false, {visibility: HIDDEN}),

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
            content: "Click on Add new Checkbox",
            trigger: 'we-list we-button.o_we_list_add_optional',
        }, {
            content: "Change last option label with a number",
            trigger: 'we-list table input:eq(3)',
            run: 'text 44 - UK',
        }, {
            content: "Check that the input value is the full option value",
            trigger: 'we-list table input:eq(3)',
            run: () => {
                const addedOptionEl = document.querySelector('.s_website_form_field select option[value="44 - UK"]');
                if (!addedOptionEl) {
                    console.error('The number option was not correctly added');
                }
            },
        }, {
            content: "Check the resulting snippet",
            trigger: ".s_website_form_field.s_website_form_custom.s_website_form_required" +
                        ":has(label:contains('State'))" +
                        ":has(select[required]:hidden)" +
                        ":has(.s_website_form_select_item:contains('Belgium'))" +
                        ":has(.s_website_form_select_item:contains('France'))" +
                        ":has(.s_website_form_select_item:contains('Canada'))" +
                        ":has(.s_website_form_select_item:contains('44 - UK'))" +
                        ":not(:has(.s_website_form_select_item:contains('Germany')))",
            run: function () {},
        },

        ...addExistingField('attachment_ids', 'file', 'Invoice Scan'),

        {
            content: "Insure the history step of the editor is not checking for unbreakable",
            trigger: '#wrapwrap',
            run: () => {
                const wysiwyg = $('#wrapwrap').data('wysiwyg');
                wysiwyg.odooEditor.historyStep(true);
            },
        },
        // Edit the submit button using linkDialog.
        {
            content: "Click submit button to show edit popover",
            trigger: '.s_website_form_send',
        }, {
            content: "Click on Edit Link in Popover",
            trigger: '.o_edit_menu_popover .o_we_edit_link',
        }, {
            content: "Check that no URL field is suggested",
            trigger: '#toolbar:has(#url_row:hidden)',
            run: () => null,
        }, {
            content: "Change button's style",
            trigger: '.dropdown-toggle[data-original-title="Link Style"]',
            run: () => {
                $('.dropdown-toggle[data-original-title="Link Style"]').click();
                $('[data-value="secondary"]').click();
                $('[data-original-title="Link Shape"]').click();
                $('[data-value="rounded-circle"]').click();
                $('[data-original-title="Link Size"]').click();
                $('[data-value="sm"]').click();
            },
        }, {
            content: "Check the resulting button",
            trigger: '.s_website_form_send.btn.btn-sm.btn-secondary.rounded-circle',
            run: () => null,
        },
        // Add a default value to a auto-fillable field.
        {
            content: 'Select the name field',
            trigger: '.s_website_form_field:eq(0)',
        }, {
            content: 'Set a default value to the name field',
            trigger: 'we-input[data-attribute-name="value"] input',
            run: 'text John Smith',
        },
        {
            content:  "Save the page",
            trigger:  "button[data-action=save]",
        },
        {
            content: 'Verify value attribute and property',
            trigger: '.s_website_form_field:eq(0) input[value="John Smith"]:propValue("Mitchell Admin")',
        },
        {
            content: 'Verify that phone field is still auto-fillable',
            trigger: '.s_website_form_field input[data-fill-with="phone"]:propValue("+1 555-555-5555")',
        },
        // Check that if we edit again and save again the default value is not deleted.
        {
            content: 'Enter in edit mode again',
            trigger: 'a[data-action="edit"]',
            run: 'click',
        },
        {
            content: 'Edit the form',
            trigger: '.s_website_form_field:eq(0) input',
            extra_trigger: 'button[data-action="save"]',
            run: 'click',
        },
        ...addCustomField('many2one', 'select', 'Select Field', true),
        {
            content: 'Save the page',
            trigger: 'button[data-action=save]',
            run: 'click',
        },
        {
            content: 'Verify that the value has not been deleted',
            trigger: '.s_website_form_field:eq(0) input[value="John Smith"]',
        },
        {
            content: 'Enter in edit mode again',
            trigger: 'a[data-action="edit"]',
            run: 'click',
        },
        {
            content: 'Click on the submit button',
            trigger: '.s_website_form_send',
            extra_trigger: 'button[data-action="save"]',
            run: 'click',
        },
        {
            content: 'Change the Recipient Email',
            trigger: '[data-field-name="email_to"] input',
            run: 'text test@test.test',
        },
        {
            content: 'Save the page',
            trigger: 'button[data-action=save]',
            run: 'click',
        },
        {
            content: 'Verify that the recipient email has been saved',
            trigger: 'body:not(.editor_enable)',
            // We have to this that way because the input type = hidden.
            extra_trigger: 'form:has(input[name="email_to"][value="test@test.test"])',
        },
    ]);

    tour.register("website_form_editor_tour_submit", {
        test: true,
    },[
        {
            content:  "Try to send the form with some required fields not filled in",
            extra_trigger:  "form[data-model_name='mail.mail']" +
                            "[data-success-page='/contactus-thank-you']" +
                            ":has(.s_website_form_field:has(label:contains('Your Name')):has(input[type='text'][name='name'][required]))" +
                            ":has(.s_website_form_field:has(label:contains('Your Email')):has(input[type='email'][name='email_from'][required]))" +
                            ":has(.s_website_form_field:has(label:contains('Your Question')):has(textarea[name='description'][required]))" +
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
                            ":has(.s_website_form_field:has(label:contains('Your Name')):not(.o_has_error))" +
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
                            ":has(.s_website_form_field:has(label:contains('Your Name')):not(.o_has_error))" +
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
                            ":has(.s_website_form_field:has(label:contains('Your Name')):not(.o_has_error))" +
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
            trigger:  "input[name='name']",
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
            trigger:  "textarea[name='description']",
            run:      "text magan"
        },
        {
            content: "Check if conditional field is visible, it shouldn't.",
            trigger: "body",
            run: function () {
                const style = window.getComputedStyle(this.$anchor[0].getElementsByClassName('s_website_form_field_hidden_if')[0]);
                if (style.display !== 'none') {
                    console.error('error This field should be invisible when the name is not odoo');
                }
            }
        },
        {
            content: "Change name input",
            trigger: "input[name='name']",
            run: "text odoo",
        },
        {
            content: "Check if conditional field is visible, it should.",
            trigger: "input[name='email_cc']",
        },
        {
            content: "Open state option",
            trigger: "select[name='State']",
            run: 'text 44 - UK',
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
                            ['body_html', 'like', 'State : 44 - UK'],
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

    function editContactUs(steps) {
        return [
            {
                content: "Enter edit mode",
                trigger: 'a[data-action=edit]',
            }, {
                content: "Select the contact us form by clicking on an input field",
                trigger: '.s_website_form input',
                extra_trigger: '#oe_snippets .oe_snippet_thumbnail',
                run: 'click',
            },
            ...steps,
            {
                content: 'Save the page',
                trigger: 'button[data-action=save]',
            },
            {
                content: 'Wait for reload',
                trigger: 'body:not(.editor_enable)',
            },
        ];
    }

    tour.register('website_form_contactus_edition_with_email', {
        test: true,
        url: '/contactus',
    }, editContactUs([
        {
            content: 'Change the Recipient Email',
            trigger: '[data-field-name="email_to"] input',
            run: 'text test@test.test',
        },
    ]));
    tour.register('website_form_contactus_edition_no_email', {
        test: true,
        url: '/contactus',
    }, editContactUs([
        {
            content: "Change a random option",
            trigger: '[data-set-mark] input',
            run: 'text_blur **',
        },
    ]));
    tour.register('website_form_contactus_submit', {
        test: true,
        url: '/contactus',
    }, [
        // As the demo portal user, only two inputs needs to be filled to send
        // the email
        {
            content: "Fill in the subject",
            trigger: 'input[name="subject"]',
        },
        {
            content: 'Fill in the message',
            trigger: 'textarea[name="description"]',
        },
        {
            content: 'Send the form',
            trigger: '.s_website_form_send',
        },
        {
            content: 'Check form is submitted without errors',
            trigger: '#wrap:has(h1:contains("Thank You!"))',
        },
    ]);

    tour.register('website_form_conditional_required_checkboxes', {
        test: true,
        url: '/',
    }, [
        // Create a form with two checkboxes: the second one required but
        // invisible when the first one is checked. Basically this should allow
        // to have: both checkboxes are visible by default but the form can
        // only be sent if one of the checkbox is checked.
        {
            content: "Enter edit mode",
            trigger: 'a[data-action=edit]',
        }, {
            content: "Add the form snippet",
            trigger: '#oe_snippets .oe_snippet:has(.s_website_form) .oe_snippet_thumbnail',
            run: 'drag_and_drop #wrap',
        }, {
            content: "Select the form by clicking on an input field",
            extra_trigger: '.s_website_form_field',
            trigger: 'section.s_website_form input',
            run: function (actions) {
                actions.auto();

                // The next steps will be about removing non essential required
                // fields. For the robustness of the test, check that amount
                // of field stays the same.
                const requiredFields = this.$anchor.closest('[data-snippet]').find('.s_website_form_required');
                if (requiredFields.length !== NB_NON_ESSENTIAL_REQUIRED_FIELDS_IN_DEFAULT_FORM) {
                    console.error('The amount of required fields seems to have changed');
                }
            },
        },
        ...((function () {
            const steps = [];
            for (let i = 0; i < NB_NON_ESSENTIAL_REQUIRED_FIELDS_IN_DEFAULT_FORM; i++) {
                steps.push({
                    content: "Select required field to remove",
                    trigger: '.s_website_form_required .s_website_form_input',
                });
                steps.push({
                    content: "Remove required field",
                    trigger: '.oe_overlay .oe_snippet_remove',
                });
            }
            return steps;
        })()),
        ...addCustomField('boolean', 'checkbox', 'Checkbox 1', false),
        ...addCustomField('boolean', 'checkbox', 'Checkbox 2', true, {visibility: CONDITIONALVISIBILITY}),
        {
            content: "Open condition item select",
            trigger: 'we-select[data-name="hidden_condition_opt"] we-toggler',
        }, {
            content: "Choose first checkbox as condition item",
            trigger: 'we-button[data-set-visibility-dependency="Checkbox 1"]',
        }, {
            content: "Open condition comparator select",
            trigger: 'we-select[data-attribute-name="visibilityComparator"] we-toggler',
        }, {
            content: "Choose 'not equal to' comparator",
            trigger: 'we-button[data-select-data-attribute="!selected"]',
        }, {
            content: 'Save the page',
            trigger: 'button[data-action=save]',
        },

        // Check that the resulting form behavior is correct
        {
            content: "Wait for page reload",
            trigger: 'body:not(.editor_enable) [data-snippet="s_website_form"]',
            run: function (actions) {
                // The next steps will be about removing non essential required
                // fields. For the robustness of the test, check that amount
                // of field stays the same.
                const essentialFields = this.$anchor.find('.s_website_form_model_required');
                if (essentialFields.length !== ESSENTIAL_FIELDS_VALID_DATA_FOR_DEFAULT_FORM.length) {
                    console.error('The amount of model-required fields seems to have changed');
                }
            },
        },
        ...essentialFieldsForDefaultFormFillInSteps,
        {
            content: 'Try sending empty form',
            trigger: '.s_website_form_send',
        }, {
            content: 'Check the form could not be sent',
            trigger: '#s_website_form_result.text-danger',
            run: () => null,
        }, {
            content: 'Check the first checkbox',
            trigger: 'input[type="checkbox"][name="Checkbox 1"]',
        }, {
            content: 'Check the second checkbox is now hidden',
            trigger: '.s_website_form:has(input[type="checkbox"][name="Checkbox 2"]:not(:visible))',
            run: () => null,
        }, {
            content: 'Try sending the form',
            trigger: '.s_website_form_send',
        }, {
            content: "Check the form was sent (success page without form)",
            trigger: 'body:not(:has([data-snippet="s_website_form"])) .fa-check-circle',
            run: () => null,
        }, {
            content: "Go back to the form",
            trigger: 'a.navbar-brand.logo',
        },
        ...essentialFieldsForDefaultFormFillInSteps,
        {
            content: 'Check the second checkbox',
            trigger: 'input[type="checkbox"][name="Checkbox 2"]',
        }, {
            content: 'Try sending the form again',
            trigger: '.s_website_form_send',
        }, {
            content: "Check the form was again sent (success page without form)",
            trigger: 'body:not(:has([data-snippet="s_website_form"])) .fa-check-circle',
            run: () => null,
        }
    ]);

    return {};
});
