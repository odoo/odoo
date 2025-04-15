/** @odoo-module */

import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";

export class DynamicModelFieldSelector extends ModelFieldSelector {

    static props = {
        ...ModelFieldSelector.props,
        record: { type: Object, optional: true },
        recordProps: { type: Object, optional: true },
    };
}
