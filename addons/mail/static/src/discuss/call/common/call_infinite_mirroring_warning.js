import { Component } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @property {Function} onClose
 * @extends {Component<Props, Env>}
 */
export class CallInfiniteMirroringWarning extends Component {
    static template = "discuss.CallInfiniteMirroringWarning";
    static props = {
        onClose: { type: Function },
    };
}
