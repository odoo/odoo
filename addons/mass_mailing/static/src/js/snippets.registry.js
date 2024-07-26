import { registerOption } from "@web_editor/js/editor/snippets.registry";

export function registerMassMailingOption(name, def, options) {
    if (!def.module) {
        def.module = "mass_mailing";
    }
    return registerOption(name, def, options);
}
