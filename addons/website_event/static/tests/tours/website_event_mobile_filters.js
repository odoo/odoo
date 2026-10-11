import { registry } from "@web/core/registry";

const movieSection = ".accordion-item:has(.accordion-button:contains(Movie))";
const languageSection = ".accordion-item:has(.accordion-button:contains(Language))";

registry.category("web_tour.tours").add("website_event_mobile_filters", {
    steps: () => [
        {
            content: "Open the mobile filters panel",
            trigger: "[data-bs-target='#o_wevent_index_offcanvas']",
            run: "click",
        },
        {
            content: "Check that every category is collapsed while nothing is filtered",
            trigger: `#o_wevent_index_offcanvas.show ${movieSection} .accordion-button[aria-expanded="false"]`,
        },
        {
            content: "Unfold the Movie category",
            trigger: `${movieSection} .accordion-button`,
            run: "click",
        },
        {
            content: "Tick Inception: the panel is refreshed in place, without reloading the page",
            trigger: `${movieSection} .form-check:has(label:contains(Inception)) input`,
            run: "click",
        },
        {
            content: "Check that every category is expanded once a filter is selected",
            trigger: `${languageSection} .accordion-collapse.show`,
        },
        {
            content: "Check that Language offers English and Hindi only, the languages Inception is in",
            trigger: `${languageSection}:has(label:contains(English)):has(label:contains(Hindi)):not(:has(label:contains(French)))`,
        },
        {
            content: "Tick Avatar too, several values of the same category can be selected",
            trigger: `${movieSection} .form-check:has(label:contains(Avatar)) input`,
            run: "click",
        },
        {
            content: "Check that both Inception and Avatar remain selected",
            trigger: `${movieSection}:has(.form-check:has(label:contains(Inception)) input:checked):has(.form-check:has(label:contains(Avatar)) input:checked)`,
        },
        {
            content: "Check that Language widened to the languages of either movie, French included",
            trigger: `${languageSection}:has(label:contains(English)):has(label:contains(Hindi)):has(label:contains(French))`,
        },
        {
            content: "Tick Hindi, a language only Inception is in: Avatar now matches nothing",
            trigger: `${languageSection} .form-check:has(label:contains(Hindi)) input`,
            run: "click",
        },
        {
            content: "Check that Avatar is no longer offered while Inception stays selected",
            trigger: `${movieSection}:has(.form-check:has(label:contains(Inception)) input:checked):not(:has(.form-check:has(label:contains(Avatar))))`,
        },
        {
            content: "Check that only the events matching both categories are listed",
            trigger:
                "#o_wevent_index_main_col:has(:contains(Inception in Hindi)):not(:has(:contains(Avatar in French)))",
        },
        {
            content: "Tick French, a language only Avatar is in",
            trigger: `${languageSection} .form-check:has(label:contains(French)) input`,
            run: "click",
        },
        {
            content: "Check that both Hindi and French remain selected, the clicked category is never pruned",
            trigger: `${languageSection}:has(.form-check:has(label:contains(Hindi)) input:checked):has(.form-check:has(label:contains(French)) input:checked)`,
        },
        {
            content: "Check that Avatar is offered again, unselected",
            trigger: `${movieSection}:has(label:contains(Avatar)):not(:has(.form-check:has(label:contains(Avatar)) input:checked))`,
        },
        {
            content: "Clear the filters",
            trigger: "#o_wevent_index_offcanvas button:contains(Clear)",
            run: "click",
        },
        {
            content: "Check that the panel stayed open and every movie with an event is offered, unselected",
            trigger: `${movieSection}:has(label:contains(Inception)):has(label:contains(Avatar)):not(:has(label:contains(Matrix))):not(:has(input:checked))`,
        },
        {
            content: "Check that no language is selected either",
            trigger: `${languageSection}:not(:has(input:checked))`,
        },
        {
            content: "Check that the categories collapsed again, the selection being empty",
            trigger: `${languageSection} .accordion-button[aria-expanded="false"]`,
            run: "click",
        },
        {
            content: "Tick French first this time",
            trigger: `${languageSection} .form-check:has(label:contains(French)) input`,
            run: "click",
        },
        {
            content: "Check that Movie is down to Avatar, the only movie in French",
            trigger: `${movieSection}:has(label:contains(Avatar)):not(:has(label:contains(Inception)))`,
        },
    ],
});
