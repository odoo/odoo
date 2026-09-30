import { getElementsWithOption } from "@html_builder/utils/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { CountdownOption } from "./countdown_option_plugin";

class CountdownExperimentOption extends CountdownOption {
    static id = "countdown_experiment_option";
    static template = "website.CountdownExperimentOption";
}

registry.category("website-options").add(CountdownExperimentOption.id, CountdownExperimentOption);

class CountdownExperimentOptionPlugin extends Plugin {
    static id = "CountdownExperimentOption";
    resources = {
        so_content_addition_selectors: [".s_countdown_experiment"],
        on_cloned_handlers: ({ cloneEl }) => {
            for (const countdownEl of getElementsWithOption(cloneEl, ".s_countdown_experiment")) {
                CountdownExperimentOption.cleanForSave(countdownEl);
            }
        },
    };
}

registry
    .category("website-plugins")
    .add(CountdownExperimentOptionPlugin.id, CountdownExperimentOptionPlugin);
