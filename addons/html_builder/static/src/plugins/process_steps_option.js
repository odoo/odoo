import { Component } from "@odoo/owl";
import { useBuilderComponents, useIsActiveItem } from "../core/utils";

export const connectorOptionParams = [
    { key: "", param: "None" },
    { key: "s_process_steps_connector_line", param: "Line" },
    { key: "s_process_steps_connector_arrow", param: "Straight arrow" },
    { key: "s_process_steps_connector_curved_arrow", param: "Curved arrow" },
];

export class ProcessStepsOption extends Component {
    static template = "html_builder.ProcessStepsOption";
    static props = {};

    setup() {
        useBuilderComponents();
        this.isActiveItem = useIsActiveItem();
        this.connectorOptionParams = connectorOptionParams;
    }

    getConnectorId(connectorOptionParamKey) {
        return !connectorOptionParamKey ? "no_connector_opt" : "";
    }
}
