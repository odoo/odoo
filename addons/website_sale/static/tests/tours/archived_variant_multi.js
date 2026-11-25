import { registry } from "@web/core/registry";
import { assertPills, pickPills } from "@website_sale/js/tours/tour_utils";

function fail(errorMessage) {
    const tour = registry.get("tourManager");
    tour._consume_tour(tour.running_tour, errorMessage);
}

function assert(current, expected, info) {
    if (current !== expected) {
        fail(info + ': "' + current + '" instead of "' + expected + '".');
    }
}

registry.category("web_tour.tours").add('website_sale.archived_variant_multi', {
    steps: () => [
        pickPills("Small"),
        pickPills("Black"),
        assertPills("Brand B", { available: false }),
        pickPills("White"),
        assertPills("Brand B", { available: true }),
        pickPills("Brand B"),
    ]
});

registry.category("web_tour.tours").add('website_sale.pills_variant', {
    steps: () => [
        {
            content: "check there are two radio boxes, both hidden",
            trigger: '.js_product',
            run: function () {
                var buttons = [...document.querySelectorAll('input.js_variant_change')];

                function isVisuallyHidden(elem) {
                    const style = window.getComputedStyle(elem);
                    return style.display === "none" ||
                        style.visibility === "hidden" ||
                        style.opacity === "0" ||
                        (style.width === "0px" && style.height === "0px")
                }

                assert(buttons.length, 2, "there should be two radio inputs")
                assert(isVisuallyHidden(buttons[0]), true, "first radio input is not hidden")
                assert(isVisuallyHidden(buttons[1]), true, "second radio input is not hidden")
                assert(buttons[0].checked, true, "first radio input should be checked")
            },
        },
        {
            content: "click on the second variant label",
            trigger: 'label:contains("Small")',
            run: "click",
        },
        {
            content: 'check second variant is selected',
            trigger: 'li.o_variant_pills.active:contains("Small")',
            run: function () {
                var button = [...document.querySelectorAll('input.js_variant_change[data-attribute-name="Size"][data-value-name="Small"]')];
                assert(button.length, 1, "there should be one radio input")
                assert(button[0].checked, true, "the radio input should be checked")
            }
        },
    ]
});
