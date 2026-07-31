/** @odoo-module **/
/*
 * Reproduction tour for the 'called ignoring args {"token"}' warning.
 * Uses ONLY native Odoo components: res.partner (base) + mail chatter
 * attachments (mail) + web.FileViewer (web). It never sends any request
 * manually — it just clicks the real Download button, letting
 * @web/core/network/download.js do exactly what it does in production.
 */
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("file_viewer_download_warning_tour", {
    steps: () => [
        {
            content: "Form view loaded directly via deep-link (no app/menu dependency)",
            trigger: ".o_form_view",
        },
        {
            content: "Wait for chatter to show the attachment",
            trigger: ".o-mail-AttachmentContainer[title='repro.txt']",
        },
        {
            content: "Click the attachment to open the real FileViewer",
            trigger: ".o-mail-AttachmentContainer[title='repro.txt']",
            run: "click",
        },
        {
            content: "FileViewer opened",
            trigger: ".o-FileViewer",
        },
        {
            content: "Click the real Download button (this runs the actual download.js code)",
            trigger: ".o-FileViewer-header .o-FileViewer-download",
            run: "click",
        },
        {
            content: "Close FileViewer",
            trigger: ".o-FileViewer .fa-times",
            run: "click",
        },
        {
            content: "FileViewer closed, tour done",
            trigger: ".o_form_view:not(:has(.o-FileViewer))",
        },
    ],
});
