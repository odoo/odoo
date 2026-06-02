import { Many2OneReferenceField } from "@web/views/fields/many2one_reference/many2one_reference_field";

import { patch } from "@web/core/utils/patch";

import { Domain } from "@web/core/domain";

patch(Many2OneReferenceField.prototype, {

    get m2oProps() {
        const props = super.m2oProps;
 
        const resModel = this.props.record.resModel;
        const relation = this.relation; 
        const resId = this.props.record.resId;

        if (resModel === 'ir.attachment' && relation === 'ir.attachment' && resId) {
            let currentDomain = props.domain || [];
            if (typeof currentDomain === "function") {
                currentDomain = currentDomain();
            }

            const baseDomain = new Domain(currentDomain);
            const excludeDomain = new Domain([['id', '!=', resId]]);

            props.domain = Domain.and([baseDomain, excludeDomain]).toList();
        }

        return props;
    }
});
