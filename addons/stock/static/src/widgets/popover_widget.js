import { Component, computed, t, useProps } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Extend this to add functionality to Popover (custom methods etc.)
 * need to extend PopoverWidgetField as well and set its Popover Component to new extension
 */
export class PopoverComponent extends Component {
    static template = "stock.popoverContent";

    props = useProps({
        msg: t.string().optional(),
        popoverTemplate: t.string().optional(),
        title: t.string(),
    });
}

/**
 * Widget Popover for JSON field (char), renders a popover above an icon button on click
 * {
 *  'msg': '<CONTENT OF THE POPOVER>' required if not 'popoverTemplate' is given,
 *  'icon': '<MATERIAL SYMBOLS NAME>' default='info',
 *  'color': '<COLOR CLASS OF ICON>' default='text-primary',
 *  'position': <POSITION OF THE POPOVER> default='top',
 *  'popoverTemplate': '<TEMPLATE OF THE POPOVER>' default='stock.popoverContent'
 *   pass a template for popover to use, other data passed in JSON field will be passed
 *   to popover template inside props (ex. props.someValue), must be owl template
 * }
 */

export class PopoverWidgetField extends Component {
    static template = "stock.popoverButton";
    static components = { Popover: PopoverComponent };

    props = useProps(standardFieldProps);

    jsonValue = computed(() => JSON.parse(this.props.record.data[this.props.name] || "{}"));
    color = computed(() => this.jsonValue().color || "text-primary");
    icon = computed(() => this.jsonValue().icon || "info");

    setup() {
        this.popover = usePopover(this.constructor.components.Popover, {
            position: this.getPosition(),
        });
    }

    getPosition() {
        return this.jsonValue().position || "top";
    }

    showPopup(ev) {
        this.popover.open(ev.currentTarget, this.jsonValue());
    }
}

export const popoverWidgetField = {
    component: PopoverWidgetField,
    supportedTypes: ["char"],
};

registry.category("fields").add("popover_widget", popoverWidgetField);
