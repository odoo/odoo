/** @odoo-module **/
import { jsonrpc } from "@web/core/network/rpc_service";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_form_editor_tour_submit", {
    test: true,
    steps: () => [
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
                        ":has(.s_website_form_field:has(input[name='email_to'][value='test@test.test']))" + 
                        ":has(.s_website_form_field:has(input[name='website_form_signature']))",
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
        content:  "Open datetime picker",
        trigger:  ".s_website_form_datetime input",
        run:      "click",
    },
    {
        content:  "Complete Date field",
        trigger:  ".o_date_picker .o_today",
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
        content: "Select state option",
        trigger: "select[name='State']",
        run: 'text 44 - UK',
    },
    {
        content:  "Send the form",
        trigger:  ".s_website_form_send"
    },
    {
        content:  "Check form is submitted without errors",
        trigger:  "#wrap:has(h1:contains('Thank You!'))",
        isCheck: true,
    }
]});

registry.category("web_tour.tours").add("website_form_editor_tour_results", {
    test: true,
    steps: () => [
    {
        content: "Check mail.mail records have been created",
        trigger: "body",
        run: function () {
            var mailDef = jsonrpc(`/web/dataset/call_kw/mail.mail/search_count`, {
                model: "mail.mail",
                method: "search_count",
                args: [[
                    ['email_to', '=', 'test@test.test'],
                    ['body_html', 'like', 'A useless message'],
                    ['body_html', 'like', 'Service : Development Service'],
                    ['body_html', 'like', 'State : 44 - UK'],
                    ['body_html', 'like', 'Products : Xperia,Wiko Stairway']
                ]],
                kwargs: {},
            });
            var success = function(model, count) {
                if (count > 0) {
                    $('body').append('<div id="website_form_editor_success_test_tour_'+model+'"></div>');
                }
            };
            mailDef.then(success.bind(this, 'mail_mail'));
        }
    },
    {
        content:  "Check mail.mail records have been created",
        trigger:  "#website_form_editor_success_test_tour_mail_mail",
        allowInvisible: true,
        isCheck: true,
    }
]});
registry.category("web_tour.tours").add('website_form_contactus_submit', {
    test: true,
    url: '/contactus',
    steps: () => [
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
        isCheck: true,
    },
]});
