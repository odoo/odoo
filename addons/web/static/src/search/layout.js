import { useRef } from "@web/owl2/utils";
import { Component, Portal, onMounted, signal } from "@odoo/owl";
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
    static components = { Portal };
    static props = {
        className: { type: String, optional: true },
        display: { type: Object, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        display: {},
    };
    footerTarget = signal(null);
    rev = 0;
    setup() {
        this.components = extractLayoutComponents(this.env.config);
        this.contentRef = useRef("content");

        onMounted(() => {
            const footer = document.querySelector(`#${this.env.dialogId} .modal-footer`);
            const hasDefaultButton = footer?.querySelector(".o-default-button");
            if (hasDefaultButton) {
                footer.replaceChildren();
            }
            this.footerTarget.set(footer);
            this.rev++;
        });
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
