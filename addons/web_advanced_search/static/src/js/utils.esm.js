/** @odoo-module **/
/*
    Copyright 2018 Tecnativa - Jairo Llopis
    Copyright 2020 Tecnativa - Alexandre Díaz
    Copyright 2022 Camptocamp SA - Iván Todorovich
    License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
*/

import {_t} from "web.core";
const JOIN_MAPPING = {
    "&": _t(" and "),
    "|": _t(" or "),
    "!": _t(" is not "),
};

const HUMAN_DOMAIN_METHODS = {
    DomainTree: function () {
        const human_domains = [];
        _.each(this.children, (child) => {
            human_domains.push(HUMAN_DOMAIN_METHODS[child.template].apply(child));
        });
        return `(${human_domains.join(JOIN_MAPPING[this.operator])})`;
    },

    DomainSelector: function () {
        const result = HUMAN_DOMAIN_METHODS.DomainTree.apply(this, arguments);
        // Remove surrounding parenthesis
        return result.slice(1, -1);
    },

    DomainLeaf: function () {
        const chain = [];
        let operator = this.operator_mapping[this.operator],
            value = `"${this.value}"`;
        // Humanize chain
        const chain_splitted = this.chain.split(".");
        const len = chain_splitted.length;
        for (let x = 0; x < len; ++x) {
            const element = chain_splitted[x];
            chain.push(
                _.findWhere(this.fieldSelector.popover.pages[x], {name: element})
                    .string || element
            );
        }
        // Special beautiness for some values
        if (this.operator === "=" && _.isBoolean(this.value)) {
            operator = this.operator_mapping[this.value ? "set" : "not set"];
            value = "";
        } else if (_.isArray(this.value)) {
            value = `["${this.value.join('", "')}"]`;
        }
        return `${chain.join("→")} ${operator || this.operator} ${value}`.trim();
    },
};

export function getHumanDomain(domainSelector) {
    return HUMAN_DOMAIN_METHODS.DomainSelector.apply(domainSelector);
}
