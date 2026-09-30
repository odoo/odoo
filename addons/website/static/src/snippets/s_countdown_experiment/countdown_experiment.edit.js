import { registry } from "@web/core/registry";
import { CountdownExperiment } from "./countdown_experiment";

registry.category("public.interactions.edit").add("website.countdown_experiment", {
    Interaction: CountdownExperiment,
});

registry.category("public.interactions.preview").add("website.countdown_experiment", {
    Interaction: CountdownExperiment,
});
