import { registerOption } from "@web_editor/js/editor/snippets.registry";

export function registerMassMailingOption(name, def, options) {
    if (!def.module) {
        def.module = "mass_mailing";
    }
    return registerOption(name, def, options);
}

registerMassMailingOption("MassMailingIconTools", {
    template: "mass_mailing.IconTools",
    selector: "span.fa, i.fa, img",
    exclude: "[data-oe-type='image'] > img, [data-oe-xpath]",
});

registerMassMailingOption("MassMailingHrOptions", {
    template: "mass_mailing.s_hr_options",
    selector: ".s_hr",
    target: "hr",
});
