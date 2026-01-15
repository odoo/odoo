import { registry } from "@web/core/registry";
import { contains } from "@web/../tests/utils";

/**
 * This tour depends on data created by python test in charge of launching it.
 * It is not intended to work when launched from interface. It is needed to test
 * an action (action manager) which is not possible to test with QUnit.
 * @see mail/tests/test_mail_composer.py
 */
registry.category("web_tour.tours").add("mail/static/tests/tours/mail_html_composer_test_tour.js", {
    steps: () => [
        {
            content: "Wait for the chatter to be fully loaded",
            trigger: ".o-mail-Chatter",
            async run() {
                const composerService = odoo.__WOWL_DEBUG__.root.env.services["mail.composer"];
                composerService.setHtmlComposer();
                await contains(".o-mail-Message", { count: 1 });
            },
        },
        {
            content: "Click on Send Message",
            trigger: "button:contains(Send message)",
            run: "click",
        },
        {
            content: "Write something in composer",
            trigger: ".o-mail-Composer-html.odoo-editor-editable",
            run: "editor Hello",
        },
        {
            content: "Select the text",
            trigger: ".o-mail-Composer-html.odoo-editor-editable",
            run: "dblclick",
        },
        {
            trigger: ".o-we-toolbar",
        },
        {
            content: "Bold the text",
            trigger: ".o-we-toolbar button[title='Toggle bold']",
            run: "click",
        },
        {
            content: "The bolded text is in the composer",
            trigger: ".o-mail-Composer-html.odoo-editor-editable strong:contains(Hello)",
        },
        {
            content: "Open full composer",
            trigger: "button[title='Open Full Composer']",
            run: "click",
        },
        {
            content: "Check composer keeps the formatted content",
            trigger: ".o_mail_composer_message strong:contains(Hello)",
        },
        {
            content: "Focus the text in full composer",
            trigger: ".o_mail_composer_message .odoo-editor-editable",
            run: "click",
        },
        {
            content: "Select the text in full composer",
            trigger: ".o_mail_composer_message .odoo-editor-editable",
            run: "dblclick",
        },
        {
            trigger: ".o-we-toolbar",
        },
        {
            content: "Remove the Bold",
            trigger: ".o-we-toolbar button[title='Toggle bold']",
            run: "click",
        },
        {
            content: "Italicize the text",
            trigger: ".o-we-toolbar button[title='Toggle italic']",
            run: "click",
        },
        {
            content: "The italicized text is in the full composer",
            trigger: ".o_mail_composer_message em:contains(Hello)",
        },
        {
            content: "Close full composer",
            trigger: ".btn-close",
            run: "click",
        },
        {
            content: "Click on Send Message",
            trigger: "button:not(.active):contains(Send message)",
            run: "click",
        },
        {
            content: "The italicized text is in the composer",
            trigger: ".o-mail-Composer-html.odoo-editor-editable em:contains(Hello)",
        },
    ],
});
