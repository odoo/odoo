import { defaultBuilderComponents } from "../core/default_builder_components";
import { Component } from "@odoo/owl";
import { useIsActiveItem } from "../core/building_blocks/utils";

export const connectorOptionParams = [
    { key: "", param: "None" },
    { key: "s_process_steps_connector_line", param: "Line" },
    { key: "s_process_steps_connector_arrow", param: "Straight arrow" },
    { key: "s_process_steps_connector_curved_arrow", param: "Curved arrow" },
];

export class ProcessStepsOption extends Component {
    static template = "html_builder.ProcessStepsOption";
    static components = { ...defaultBuilderComponents };
    static props = {};

    setup() {
        this.isActiveItem = useIsActiveItem();
        this.connectorOptionParams = connectorOptionParams;
    }

    getConnectorId(connectorOptionParamKey) {
        return !connectorOptionParamKey ? "no_connector_opt" : "";
    }
}
