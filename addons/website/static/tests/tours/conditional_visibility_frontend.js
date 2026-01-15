import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("conditional_visibility_2", {
    url: "/?utm_medium=Email",
    steps: () => [
        {
            content: "The content previously hidden should now be visible",
            trigger: "body #wrapwrap",
            run: function (actions) {
                const style = window.getComputedStyle(
                    this.anchor.getElementsByClassName("s_text_image")[0]
                );
                if (style.display === "none") {
                    console.error(
                        "error This item should now be visible because utm_medium === email"
                    );
                }
            },
        },
    ],
});
