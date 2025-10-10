import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_account_log_cancellation", {
    steps: () => [
        {
            content: "Click Cancel Button",
            trigger: ".o-mail-Scheduled-Message-buttons .fa-times",
            run: "click",
        },
        {
            content: "Click confirm button",
            trigger: ".modal-footer .btn-primary",
            run: "click",
        },
    ],
});
