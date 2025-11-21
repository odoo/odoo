import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { usePopover } from "@web/core/popover/popover_hook";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import {
    Many2ManyTagsField,
    many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { TaxTagPopup } from "./tax_tag_popover"

export class Many2XTaxTagsAutocomplete extends Many2XAutocomplete {
    static components = {
        ...Many2XAutocomplete.components,
    };

    async loadOptionsSource(request) {
        // Always include Search More
        let options = await super.loadOptionsSource(...arguments);
        if (!options.slice(-1)[0]?.cssClass?.includes("o_m2o_dropdown_option_search_more")) {
            options.push({
                label: this.SearchMoreButtonLabel,
                onSelect: this.onSearchMore.bind(this, request),
                cssClass: "o_m2o_dropdown_option o_m2o_dropdown_option_search_more",
            });
        }
        return options;
    }

    async onSearchMore(request) {
        const { getDomain, context, fieldString } = this.props;

        const domain = getDomain();
        let dynamicFilters = [];
        if (request.length) {
            dynamicFilters = [
                {
                    description: _t("Quick search: %s", request),
                    domain: [["name", "ilike", request]],
                },
            ];
        }

        const title = _t("Search: %s", fieldString);
        this.selectCreate({
            domain,
            context,
            filters: dynamicFilters,
            title,
        });
    }

}

export class Many2ManyTaxTagsField extends Many2ManyTagsField {
    static components = {
        ...Many2ManyTagsField.components,
        Many2XAutocomplete: Many2XTaxTagsAutocomplete,
    };

    setup() {
        super.setup();
        this.taxPopover = usePopover(TaxTagPopup, {
            animation: false,
        });
    }

    getTagProps(record) {
        const props = super.getTagProps(record);
        props.onClick = (ev) => this.onTagClick(ev, record);
        return props;
    }

    async onTagClick(ev, record) {
        const specification = {
            display_name: {},
            description: {},
            invoice_repartition_line_ids: {
                fields: {
                    repartition_type: {},
                    factor_percent: {},
                    tag_ids: {
                        fields: {
                            name: {},
                        },
                    },
                },
            },
            refund_repartition_line_ids: {
                fields: {
                    repartition_type: {},
                    factor_percent: {},
                    tag_ids: {
                        fields: {
                            name: {},
                        },
                    },
                },
            },
        };

        const [taxData] = await this.orm.webRead("account.tax", [record.resId], { specification });

        taxData.description = taxData.description
            ? taxData.description.replace(/<[^>]+>/g, "").trim()
            : "";

        const groupByType = (lines) => {
            const groups = {};
            for (const line of lines) {
                if (!groups[line.repartition_type]) {
                    groups[line.repartition_type] = {
                        type: line.repartition_type,
                        lines: [],
                    };
                }

                groups[line.repartition_type].lines.push({
                    factor_percent:
                        Math.abs(line.factor_percent) !== 100 ? line.factor_percent : null,
                    tag_names: (line.tag_ids || []).map((tag) => tag.name),
                });
            }
            return Object.values(groups);
        };

        this.taxPopover.open(ev.target, {
            description: taxData.description,
            invoiceLines: groupByType(taxData.invoice_repartition_line_ids),
            refundLines: groupByType(taxData.refund_repartition_line_ids),
            close: () => this.taxPopover.close(),
        });
    }
}

export const many2ManyTaxTagsField = {
    ...many2ManyTagsField,
    component: Many2ManyTaxTagsField,
    additionalClasses: ['o_field_many2many_tags']
};

registry.category("fields").add("many2many_tax_tags", many2ManyTaxTagsField);
