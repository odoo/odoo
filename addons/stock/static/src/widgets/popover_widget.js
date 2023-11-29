/** @odoo-module */
import { registry } from "@web/core/registry";
import { usePopover } from "@web/core/popover/popover_hook";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Extend this to add functionality to Popover (custom methods etc.)
 * need to extend PopoverWidgetField as well and set its Popover Component to new extension
 */
export class PopoverComponent extends Component {
    static template = "stock.popoverContent";
    static props = ["record", "*"];
}

/**
 * Widget Popover for JSON field (char), renders a popover above an icon button on click
 * {
 *  'msg': '<CONTENT OF THE POPOVER>' required if not 'popoverTemplate' is given,
 *  'icon': '<FONT AWESOME CLASS>' default='fa-info-circle',
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
    static props = {...standardFieldProps};
    setup(){
        let fieldValue = this.props.record.data[this.props.name];
        this.jsonValue = JSON.parse(fieldValue || "{}");
        const position = this.jsonValue.position || "top";
        this.popover = usePopover(this.constructor.components.Popover, { position });
        this.color = this.jsonValue.color || 'text-primary';
        this.icon = this.jsonValue.icon || 'fa-info-circle';
    }

    showPopup(ev){
        this.popover.open(ev.currentTarget, { ...this.jsonValue, record: this.props.record });
    }
}

export const popoverWidgetField = {
    component: PopoverWidgetField,
    supportedTypes: ['char'],
};

registry.category("fields").add("popover_widget", popoverWidgetField);
