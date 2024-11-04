import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('tests_shared_js_python', {
    url: "/account/init_tests_shared_js_python",
    steps: () => [
    {
        content: "Click",
        trigger: 'button',
        run: "click",
    },
    {
        content: "Wait",
        trigger: 'button.text-success',
        timeout: 3000,
    },
]});
