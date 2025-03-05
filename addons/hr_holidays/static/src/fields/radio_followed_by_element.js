import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { RadioField, radioField } from "@web/views/fields/radio/radio_field";
import {onMounted,onWillUnmount} from "@odoo/owl";

export class RadioFollowedByElement extends RadioField {
    static props = {
        ...RadioField.props,
        links: { type: Object },
        observe: { type: String },
    };
    setup() {
        super.setup(...arguments);

        onMounted(() => {
            this.moveElement();
            this.observer = new MutationObserver((mutations) => {
                if ([...mutations].map(mutation =>
                    [...mutation.addedNodes].map(node => node.id))
                    .flat()
                    .filter(id => Object.values(this.props.links).includes(id))) this.moveElement();
            });

            this.observer.observe(document.getElementsByName(this.props.observe).item(0), {
                childList: true,
                subtree: true,
                attributes: false,
                characterData: false,
            });
        });

        onWillUnmount(() => {
            this.observer.disconnect();
        });
    }

    moveElement() {
        for (const [key, value] of Object.entries(this.props.links)) {
            const option = document.querySelectorAll("[data-value="+key+"]")[0];
            const elementToAppend = document.getElementById(value);
            if (option === null || elementToAppend === null || elementToAppend.parentElement === option.parentElement)
                continue;
            option.parentElement.appendChild(elementToAppend);
        }
    }
}

export const radioFollowedByElement = {
    ...radioField,
    component: RadioFollowedByElement,
    displayName: _t("Radio followed by element"),
    supportedOptions: [
        {
            label: _t("Element association"),
            name: "links",
            type: "Object",
            help: _t("An object to link select options and element id to move"),
        },
        {
            label: _t("Element to observe"),
            name: "observe",
            type: "String",
            help: _t("An element name parent of the radio to observe updates"),
        }
    ],
    extractProps({ options }, dynamicInfo) {
        return {
            readonly: dynamicInfo.readonly,
            links: options.links,
            observe: options.observe,
        };
    },
};

registry.category("fields").add("radio_followed_by_element", radioFollowedByElement);
