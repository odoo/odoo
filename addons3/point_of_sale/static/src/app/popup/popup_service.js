/** @odoo-module */

import { Component, reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class PopupContainer extends Component {
    static template = "point_of_sale.PopupContainer";
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
        let zIndex = 10000;
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
                    zIndex++;
                    popups[id] = {
                        component,
                        props: {
                            zIndex,
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
