import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatMonetary } from "@web/views/fields/formatters";

export const productSnapshotSnippetInfo = {
    fields: [
        "id",
        "display_name",
        "name",
        "description_sale",
        "list_price",
        "currency_id",
        "standard_price",
    ],
    get modelDisplayName() {
        return _t("Product");
    },
    getSnippetName: (key) => {
        switch (key) {
            case "columns":
                return "mass_mailing_sale.s_product_snapshot_columns_fragment";
            case "card":
                return "mass_mailing_sale.s_product_snapshot_card_fragment";
            case "aside":
                return "mass_mailing_sale.s_product_snapshot_aside_fragment";
        }
    },
    additionalRenderingContext: async (record) => ({
        standardPrice: formatMonetary(record.standard_price, {
            currencyId: record.currency_id[0],
            trailingZeros: false,
        }),
        listPrice: formatMonetary(record.list_price, {
            currencyId: record.currency_id[0],
            trailingZeros: false,
        }),
    }),
};

registry
    .category("mass_mailing.record-snapshot-snippet-info")
    .add("product.template", productSnapshotSnippetInfo);
