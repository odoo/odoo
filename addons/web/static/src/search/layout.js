import { useRef } from "@web/owl2/utils";
import { Component, props, t } from "@odoo/owl";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { SearchPanel } from "@web/search/search_panel/search_panel";

/**
 * @param {Object} params
 * @returns {Object}
 */
export function extractLayoutComponents(params) {
    const layoutComponents = {
        ControlPanel: params.ControlPanel || ControlPanel,
        SearchPanel: params.SearchPanel || SearchPanel,
    };
    return layoutComponents;
}

export class Layout extends Component {
    static template = "web.Layout";
    props = props({
        className: t.string().optional(),
        display: t.object().optional({}),
        slots: t.object().optional(),
    });
    setup() {
        this.components = extractLayoutComponents(this.env.config);
        this.contentRef = useRef("content");
    }
    get controlPanelSlots() {
        const slots = { ...this.props.slots };
        if (this.env.inDialog) {
            delete slots["control-panel-buttons"];
        }
        delete slots.default;
        return slots;
    }
}
