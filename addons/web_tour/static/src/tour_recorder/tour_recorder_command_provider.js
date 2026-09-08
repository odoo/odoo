import { usePlugin } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { TourRecorderPlugin } from "./tour_recorder_plugin";

registry.category("command_provider").add("tour_recorder", {
    provide: (env, options) => {
        const recorder = usePlugin(TourRecorderPlugin);
        const result = [];
        if (options.searchValue.toLowerCase() === "record") {
            result.push({
                action() {
                    recorder.startTourRecorder();
                },
                name: _t("Enable the tour recorder"),
            });
        }
        return result;
    },
});
