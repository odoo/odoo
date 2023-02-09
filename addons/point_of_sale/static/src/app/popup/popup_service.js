/** @odoo-module */

import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { LegacyComponent } from "@web/legacy/legacy_component";
import { usePos } from "@point_of_sale/app/pos_hook";
export class PopupContainer extends LegacyComponent {
    static template = "point_of_sale.PopupContainer";
    setup() {
        // FIXME POSREF: remove this after LegacyComponent is removed.
        this.__owl__.childEnv = usePos().legacyEnv;
    }
}

// FIXME POSREF: probably should use the main dialog service from web long term.
export const popupService = {
    start() {
        const popups = reactive({});
        registry.category("main_components").add("PopupContainer", {
            Component: PopupContainer,
            props: { popups },
        });
        let popupId = 0;
        return {
            /**
             * Displays a popup over the interface.
             *
             * @param {AbstractAwaitablePopup} component the popup component to
             *  open
             * @param {Object} props props for the popup component
             * @returns {Promise<any>} a Promise that fulfills when the popup
             *  is closed (confirmed or canceled)
             */
            add(component, props) {
                return new Promise((resolve) => {
                    const id = ++popupId;
                    popups[id] = {
                        component,
                        props: {
                            keepBehind: false,
                            cancelKey: "Escape",
                            confirmKey: "Enter",
                            // FIXME POSREF assigning the default props by hand defeats the point of default props
                            ...component.defaultProps,
                            ...props,
                            id,
                            resolve,
                            close(response) {
                                delete popups[id];
                                resolve(response);
                            },
                        },
                    };
                });
            },
            // exposed so that overrides can use it, should not be read from outside. Maybe we should just implement closePopupsButError directly in pos instead of pos_restaurant
            popups,
        };
    },
};

registry.category("services").add("popup", popupService);
