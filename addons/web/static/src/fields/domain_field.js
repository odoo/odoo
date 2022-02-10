/** @odoo-module **/

import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Domain } from "@web/core/domain";
import { CharField } from "./char_field";
import { standardFieldProps } from "./standard_field_props";

const { Component, onWillStart, onWillUpdateProps, useState } = owl;

export class DomainField extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            recordCount: null,
            isValid: true,
        });

        onWillStart(() => {
            this.loadCount(this.props);
        });
        onWillUpdateProps((nextProps) => {
            this.loadCount(nextProps);
        });
    }

    get isValidDomain() {
        try {
            this.getDomain(this.props.value).toList();
            return true;
        } catch (e) {
            return false;
        }
    }

    getResModel(props) {
        if (props.record.fieldNames.includes(props.model)) {
            return props.record.data[props.model];
        }
        return props.model;
    }
    getDomain(value) {
        return new Domain(value || "[]");
    }
    async loadCount(props) {
        if (!this.getResModel(props)) {
            Object.assign(this.state, {
                recordCount: 0,
                isValid: true,
            });
        }

        try {
            this.state.recordCount = null;
            const context = props.record.getFieldContext(props.name);
            Object.assign(this.state, {
                recordCount: await this.orm.silent.call(
                    this.getResModel(props),
                    "search_count",
                    [this.getDomain(props.value).toList(context)],
                    { context }
                ),
                isValid: true,
            });
        } catch (e) {
            Object.assign(this.state, {
                recordCount: 0,
                isValid: false,
            });
        }
    }
}

Object.assign(DomainField, {
    template: "web.DomainField",
    props: {
        ...standardFieldProps,
        model: { type: String, optional: true },
    },
    components: {
        CharField,
        DomainSelector,
    },

    supportedTypes: ["char"],

    isEmpty() {
        return false;
    },
    convertAttrsToProps(attrs) {
        return {
            model: attrs.options.model,
        };
    },
});

registry.category("fields").add("domain", DomainField);
