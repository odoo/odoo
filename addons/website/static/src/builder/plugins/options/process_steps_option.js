import { BaseOptionComponent } from "@html_builder/core/utils";

export const connectorOptionParams = [
    { key: "", param: "None" },
    { key: "s_process_steps_connector_line", param: "Line" },
    { key: "s_process_steps_connector_arrow", param: "Straight arrow" },
    { key: "s_process_steps_connector_curved_arrow", param: "Curved arrow" },
];

export class ProcessStepsOption extends BaseOptionComponent {
    static template = "website.ProcessStepsOption";
    static selector = ".s_process_steps";

    setup() {
        super.setup();
        this.connectorOptionParams = connectorOptionParams;
    }

    getConnectorId(connectorOptionParamKey) {
        return !connectorOptionParamKey ? "no_connector_opt" : "";
    }
}
