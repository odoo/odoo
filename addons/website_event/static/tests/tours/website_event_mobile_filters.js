import { registry } from "@web/core/registry";

const movieSection = ".accordion-item:has(.accordion-button:contains(Movie))";
const languageSection = ".accordion-item:has(.accordion-button:contains(Language))";

registry.category("web_tour.tours").add("website_event_mobile_filters", {
    steps: () => [
        {
            content: "Open the mobile filters panel, which only exists below the lg breakpoint",
            trigger: "button[data-bs-target='#o_wevent_index_offcanvas']",
            run: "click",
        },
        {
            content: "Nothing is filtered yet, so every category is collapsed",
            trigger: `#o_wevent_index_offcanvas.show ${movieSection} .accordion-button[aria-expanded="false"]`,
        },
        {
            content: "Unfold the Movie category to reach its values",
            trigger: `${movieSection} .accordion-button`,
            run: "click",
        },
        {
            content: "Tick Inception: the panel is refreshed in place, without reloading the page",
            trigger: `${movieSection} .form-check:has(label:contains(Inception)) input`,
            run: "click",
        },
        {
            content: "Filtering started, so every category opens to show what it offers",
            trigger: `${languageSection} .accordion-collapse.show`,
        },
        {
            content:
                "Language now offers English and Hindi only, the languages Inception is in, and no longer French",
            trigger: `${languageSection}:has(label:contains(English)):has(label:contains(Hindi)):not(:has(label:contains(French)))`,
        },
        {
            content:
                "Movie still offers Avatar: a category is never narrowed by its own selection, since its values are OR-ed",
            trigger: `${movieSection}:has(label:contains(Avatar))`,
        },
        {
            content: "Tick Avatar too, several values of the same category can be selected",
            trigger: `${movieSection} .form-check:has(label:contains(Avatar)) input`,
            run: "click",
        },
        {
            content: "Both movies stay ticked, the selection is not replaced by the last click",
            trigger: `${movieSection}:has(.form-check:has(label:contains(Inception)) input:checked):has(.form-check:has(label:contains(Avatar)) input:checked)`,
        },
        {
            content: "Language widened to the languages of either movie, French included",
            trigger: `${languageSection}:has(label:contains(English)):has(label:contains(Hindi)):has(label:contains(French))`,
        },
        {
            content: "Tick Hindi, a language only Inception is in: Avatar now matches nothing",
            trigger: `${languageSection} .form-check:has(label:contains(Hindi)) input`,
            run: "click",
        },
        {
            content:
                "Avatar no longer narrows anything, so it drops out of the selection while Inception stays",
            trigger: `${movieSection}:has(.form-check:has(label:contains(Inception)) input:checked):not(:has(.form-check:has(label:contains(Avatar)) input:checked))`,
        },
        {
            content: "The results are the events matching both categories: Inception in Hindi only",
            trigger:
                "#o_wevent_index_main_col:has(:contains(Inception in Hindi)):not(:has(:contains(Avatar in French)))",
        },
        {
            content: "Tick French, a language only Avatar is in",
            trigger: `${languageSection} .form-check:has(label:contains(French)) input`,
            run: "click",
        },
        {
            content: "The clicked category keeps both of its values, it is never pruned",
            trigger: `${languageSection}:has(.form-check:has(label:contains(Hindi)) input:checked):has(.form-check:has(label:contains(French)) input:checked)`,
        },
        {
            content: "Avatar is offered again, unticked: some language of it is now selected",
            trigger: `${movieSection}:has(label:contains(Avatar)):not(:has(.form-check:has(label:contains(Avatar)) input:checked))`,
        },
        {
            content: "Clear the filters, the panel stays open",
            trigger: "#o_wevent_index_offcanvas button:contains(Clear)",
            run: "click",
        },
        {
            content:
                "Every movie having an event is offered again, Matrix has none, and none is ticked",
            trigger: `${movieSection}:has(label:contains(Inception)):has(label:contains(Avatar)):not(:has(label:contains(Matrix))):not(:has(input:checked))`,
        },
        {
            content: "No language is ticked either, Clear emptied every category",
            trigger: `${languageSection}:not(:has(input:checked))`,
        },
        {
            content: "Clearing emptied the selection, so the categories collapsed again",
            trigger: `${languageSection} .accordion-button[aria-expanded="false"]`,
            run: "click",
        },
        {
            content: "Tick French first this time, the categories narrow each other symmetrically",
            trigger: `${languageSection} .form-check:has(label:contains(French)) input`,
            run: "click",
        },
        {
            content: "Movie is down to Avatar, the only movie in French",
            trigger: `${movieSection}:has(label:contains(Avatar)):not(:has(label:contains(Inception)))`,
        },
    ],
});
