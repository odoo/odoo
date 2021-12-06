/** @odoo-module **/

import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Domain } from "@web/core/domain";
import { CharField } from "./char_field";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class DomainField extends Component {
    setup() {
        this.orm = useService("orm");
        this.recordCount = null;
    }
    async willStart() {
        this.recordCount = await this.orm.call(this.resModel, "search_count", [
            this.getDomain(this.props.value).toList(),
        ]);
    }
    async willUpdateProps(nextProps) {
        this.recordCount = await this.orm.call(this.resModel, "search_count", [
            this.getDomain(nextProps.value).toList(),
        ]);
    }

    get resModel() {
        return this.props.options.model || this.props.record.resModel;
    }

    getDomain(value) {
        return new Domain(value || "[]");
    }
}

Object.assign(DomainField, {
    template: "web.DomainField",
    props: {
        ...standardFieldProps,
    },
    components: {
        CharField,
        DomainSelector,
    },

    supportedTypes: ["char"],
});

registry.category("fields").add("domain", DomainField);
