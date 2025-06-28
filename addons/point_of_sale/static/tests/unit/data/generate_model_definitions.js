import { defineModels, MockServer, models } from "@web/../tests/web_test_helpers";

export const modelsToLoad = [
    "pos.config",
    "pos.session",
    "pos.preset",
    "resource.calendar.attendance",
    "pos.order",
    "pos.order.line",
    "pos.pack.operation.lot",
    "pos.payment",
    "pos.payment.method",
    "pos.printer",
    "pos.category",
    "pos.bill",
    "res.company",
    "account.tax",
    "account.tax.group",
    "product.template",
    "product.product",
    "product.attribute",
    "product.attribute.custom.value",
    "product.template.attribute.line",
    "product.template.attribute.value",
    "product.template.attribute.exclusion",
    "product.combo",
    "product.combo.item",
    "res.users",
    "res.partner",
    "product.uom",
    "decimal.precision",
    "uom.uom",
    "res.country",
    "res.country.state",
    "res.lang",
    "product.category",
    "product.pricelist",
    "product.pricelist.item",
    "account.cash.rounding",
    "account.fiscal.position",
    "stock.picking.type",
    "res.currency",
    "pos.note",
    "product.tag",
    "ir.module.module",
];

export class PosSession extends models.ServerModel {
    _name = "pos.session";

    _load_pos_data_fields() {
        return [
            "id",
            "name",
            "user_id",
            "config_id",
            "start_at",
            "stop_at",
            "payment_method_ids",
            "state",
            "update_stock_at_closing",
            "cash_register_balance_start",
            "access_token",
        ];
    }
}

export class PosConfig extends models.ServerModel {
    _name = "pos.config";

    _load_pos_data_fields() {
        return [];
    }
}

export class PosPreset extends models.ServerModel {
    _name = "pos.preset";

    _load_pos_data_fields() {
        return [
            "id",
            "name",
            "pricelist_id",
            "fiscal_position_id",
            "is_return",
            "color",
            "has_image",
            "write_date",
            "identification",
            "use_timing",
            "slots_per_interval",
            "interval_time",
            "attendance_ids",
        ];
    }
}

export class ResourceCalendarAttendance extends models.ServerModel {
    _name = "resource.calendar.attendance";

    _load_pos_data_fields() {
        return ["id", "hour_from", "hour_to", "dayofweek", "day_period"];
    }
}

export class PosOrder extends models.ServerModel {
    _name = "pos.order";

    _load_pos_data_fields() {
        return [];
    }
}

export class PosOrderLine extends models.ServerModel {
    _name = "pos.order.line";

    _load_pos_data_fields() {
        return [
            "qty",
            "attribute_value_ids",
            "custom_attribute_value_ids",
            "price_unit",
            "uuid",
            "price_subtotal",
            "price_subtotal_incl",
            "order_id",
            "note",
            "price_type",
            "product_id",
            "discount",
            "tax_ids",
            "pack_lot_ids",
            "customer_note",
            "refunded_qty",
            "price_extra",
            "full_product_name",
            "refunded_orderline_id",
            "combo_parent_id",
            "combo_line_ids",
            "combo_item_id",
            "refund_orderline_ids",
            "extra_tax_data",
            "write_date",
        ];
    }
}

export class PosPackOperationLot extends models.ServerModel {
    _name = "pos.pack.operation.lot";

    _load_pos_data_fields() {
        return ["lot_name", "pos_order_line_id", "write_date"];
    }
}

export class PosPayment extends models.ServerModel {
    _name = "pos.payment";

    _load_pos_data_fields() {
        return [];
    }
}

export class PosPaymentMethod extends models.ServerModel {
    _name = "pos.payment.method";

    _load_pos_data_fields() {
        return [
            "id",
            "name",
            "is_cash_count",
            "use_payment_terminal",
            "split_transactions",
            "type",
            "image",
            "sequence",
            "payment_method_type",
            "default_qr",
        ];
    }
}

export class PosPrinter extends models.ServerModel {
    _name = "pos.printer";

    _load_pos_data_fields() {
        return ["id", "name", "proxy_ip", "product_categories_ids", "printer_type"];
    }
}

export class PosCategory extends models.ServerModel {
    _name = "pos.category";

    _load_pos_data_fields() {
        return [
            "id",
            "name",
            "parent_id",
            "child_ids",
            "write_date",
            "has_image",
            "color",
            "sequence",
            "hour_until",
            "hour_after",
        ];
    }
}

export class PosBill extends models.ServerModel {
    _name = "pos.bill";

    _load_pos_data_fields() {
        return ["id", "name", "value"];
    }
}

export class ResCompany extends models.ServerModel {
    _name = "res.company";

    _load_pos_data_fields() {
        return [
            "id",
            "currency_id",
            "email",
            "website",
            "company_registry",
            "vat",
            "name",
            "phone",
            "partner_id",
            "country_id",
            "state_id",
            "tax_calculation_rounding_method",
            "nomenclature_id",
            "point_of_sale_use_ticket_qr_code",
            "point_of_sale_ticket_unique_code",
            "point_of_sale_ticket_portal_url_display_mode",
            "street",
            "city",
            "zip",
            "account_fiscal_country_id",
        ];
    }
}

export class AccountTax extends models.ServerModel {
    _name = "account.tax";

    _load_pos_data_fields() {
        return [
            "id",
            "name",
            "price_include",
            "include_base_amount",
            "is_base_affected",
            "has_negative_factor",
            "amount_type",
            "children_tax_ids",
            "amount",
            "company_id",
            "id",
            "sequence",
            "tax_group_id",
        ];
    }
}

export class AccountTaxGroup extends models.ServerModel {
    _name = "account.tax.group";

    _load_pos_data_fields() {
        return ["id", "name", "pos_receipt_label"];
    }
}

export class ProductTemplate extends models.ServerModel {
    _name = "product.template";

    _load_pos_data_fields() {
        return [
            "id",
            "display_name",
            "standard_price",
            "categ_id",
            "pos_categ_ids",
            "taxes_id",
            "barcode",
            "name",
            "list_price",
            "is_favorite",
            "default_code",
            "to_weight",
            "uom_id",
            "description_sale",
            "description",
            "tracking",
            "type",
            "service_tracking",
            "is_storable",
            "write_date",
            "color",
            "pos_sequence",
            "available_in_pos",
            "attribute_line_ids",
            "active",
            "image_128",
            "combo_ids",
            "product_variant_ids",
            "public_description",
            "pos_optional_product_ids",
            "sequence",
            "product_tag_ids",
        ];
    }
}

export class ProductProduct extends models.ServerModel {
    _name = "product.product";

    // NOTE - We don't take into account _eval_taxes_computation_prepare_product_fields
    _load_pos_data_fields() {
        return [
            "id",
            "lst_price",
            "display_name",
            "product_tmpl_id",
            "product_template_variant_value_ids",
            "product_template_attribute_value_ids",
            "barcode",
            "product_tag_ids",
            "default_code",
            "standard_price",
        ];
    }
}

export class ProductAttribute extends models.ServerModel {
    _name = "product.attribute";

    _load_pos_data_fields() {
        return [
            "name",
            "display_type",
            "template_value_ids",
            "attribute_line_ids",
            "create_variant",
        ];
    }
}

export class ProductAttributeCustomValue extends models.ServerModel {
    _name = "product.attribute.custom.value";

    _load_pos_data_fields() {
        return [
            "custom_value",
            "custom_product_template_attribute_value_id",
            "pos_order_line_id",
            "write_date",
        ];
    }
}

export class ProductTemplateAttributeLine extends models.ServerModel {
    _name = "product.template.attribute.line";

    _load_pos_data_fields() {
        return ["display_name", "attribute_id", "product_template_value_ids"];
    }
}

export class ProductTemplateAttributeValue extends models.ServerModel {
    _name = "product.template.attribute.value";

    _load_pos_data_fields() {
        return [
            "attribute_id",
            "attribute_line_id",
            "product_attribute_value_id",
            "price_extra",
            "name",
            "is_custom",
            "html_color",
            "image",
            "exclude_for",
        ];
    }
}

export class ProductTemplateAttributeExclusion extends models.ServerModel {
    _name = "product.template.attribute.exclusion";

    _load_pos_data_fields() {
        return ["value_ids", "product_template_attribute_value_id"];
    }
}

export class ProductCombo extends models.ServerModel {
    _name = "product.combo";

    _load_pos_data_fields() {
        return ["id", "name", "combo_item_ids", "base_price", "qty_free", "qty_max"];
    }
}

export class ProductComboItem extends models.ServerModel {
    _name = "product.combo.item";

    _load_pos_data_fields() {
        return ["id", "combo_id", "product_id", "extra_price"];
    }
}

export class ResUsers extends models.ServerModel {
    _name = "res.users";

    _load_pos_data_fields() {
        return ["id", "name", "partner_id", "all_group_ids"];
    }
}

export class ResPartner extends models.ServerModel {
    _name = "res.partner";

    _load_pos_data_fields() {
        return [
            "id",
            "name",
            "street",
            "street2",
            "city",
            "state_id",
            "country_id",
            "vat",
            "lang",
            "phone",
            "zip",
            "email",
            "barcode",
            "write_date",
            "property_product_pricelist",
            "parent_name",
            "pos_contact_address",
            "invoice_emails",
            "company_type",
            "fiscal_position_id",
        ];
    }
}

export class ProductUom extends models.ServerModel {
    _name = "product.uom";

    _load_pos_data_fields() {
        return ["id", "barcode", "product_id", "uom_id"];
    }
}

export class DecimalPrecision extends models.ServerModel {
    _name = "decimal.precision";

    _load_pos_data_fields() {
        return ["id", "name", "digits"];
    }
}

export class UomUom extends models.ServerModel {
    _name = "uom.uom";

    _load_pos_data_fields() {
        return ["id", "name", "factor", "is_pos_groupable", "parent_path", "rounding"];
    }
}

export class ResCountry extends models.ServerModel {
    _name = "res.country";

    _load_pos_data_fields() {
        return ["id", "name", "code", "vat_label"];
    }
}

export class ResCountryState extends models.ServerModel {
    _name = "res.country.state";

    _load_pos_data_fields() {
        return ["id", "name", "code", "country_id"];
    }
}

export class ResLang extends models.ServerModel {
    _name = "res.lang";

    _load_pos_data_fields() {
        return ["id", "name", "code", "flag_image_url", "display_name"];
    }
}

export class ProductCategory extends models.ServerModel {
    _name = "product.category";

    _load_pos_data_fields() {
        return ["id", "name", "parent_id"];
    }
}

export class ProductPricelist extends models.ServerModel {
    _name = "product.pricelist";

    _load_pos_data_fields() {
        return ["id", "name", "display_name", "item_ids"];
    }
}

export class ProductPricelistItem extends models.ServerModel {
    _name = "product.pricelist.item";

    _load_pos_data_fields() {
        return [
            "product_tmpl_id",
            "product_id",
            "pricelist_id",
            "price_surcharge",
            "price_discount",
            "price_round",
            "price_min_margin",
            "price_max_margin",
            "company_id",
            "currency_id",
            "date_start",
            "date_end",
            "compute_price",
            "fixed_price",
            "percent_price",
            "base_pricelist_id",
            "base",
            "categ_id",
            "min_quantity",
        ];
    }
}

export class AccountCashRounding extends models.ServerModel {
    _name = "account.cash.rounding";

    _load_pos_data_fields() {
        return [];
    }
}

export class AccountFiscalPosition extends models.ServerModel {
    _name = "account.fiscal.position";

    _load_pos_data_fields() {
        return ["id", "name", "display_name", "tax_map"];
    }
}

export class StockPickingType extends models.ServerModel {
    _name = "stock.picking.type";

    _load_pos_data_fields() {
        return ["id", "use_create_lots", "use_existing_lots"];
    }
}

export class ResCurrency extends models.ServerModel {
    _name = "res.currency";

    _load_pos_data_fields() {
        return [
            "id",
            "name",
            "symbol",
            "position",
            "rounding",
            "rate",
            "decimal_places",
            "iso_numeric",
        ];
    }
}

export class PosNote extends models.ServerModel {
    _name = "pos.note";

    _load_pos_data_fields() {
        return ["name", "color"];
    }
}

export class ProductTag extends models.ServerModel {
    _name = "product.tag";

    _load_pos_data_fields() {
        return ["name", "pos_description", "color", "has_image", "write_date"];
    }
}

export class IrModuleModule extends models.ServerModel {
    _name = "ir.module.module";

    _load_pos_data_fields() {
        return ["id", "name", "state"];
    }
}

export const posModels = [
    PosSession,
    PosConfig,
    PosPreset,
    ResourceCalendarAttendance,
    PosOrder,
    PosOrderLine,
    PosPackOperationLot,
    PosPayment,
    PosPaymentMethod,
    PosPrinter,
    PosCategory,
    PosBill,
    ResCompany,
    AccountTax,
    AccountTaxGroup,
    ProductTemplate,
    ProductProduct,
    ProductAttribute,
    ProductAttributeCustomValue,
    ProductTemplateAttributeLine,
    ProductTemplateAttributeValue,
    ProductTemplateAttributeExclusion,
    ProductCombo,
    ProductComboItem,
    ResUsers,
    ResPartner,
    ProductUom,
    DecimalPrecision,
    UomUom,
    ResCountry,
    ResCountryState,
    ResLang,
    ProductCategory,
    ProductPricelist,
    ProductPricelistItem,
    AccountCashRounding,
    AccountFiscalPosition,
    StockPickingType,
    ResCurrency,
    PosNote,
    ProductTag,
    IrModuleModule,
];

defineModels(posModels);

const prepareModelDefinitionObjects = () =>
    modelsToLoad.reduce((acc, modelName) => {
        acc[modelName] = {};
        return acc;
    }, {});

export const getPosModelDefinitions = () => {
    const fields = prepareModelDefinitionObjects();
    const relations = prepareModelDefinitionObjects();

    for (const model of posModels) {
        const posFields = MockServer.env[model._name]._load_pos_data_fields();
        const allFields = MockServer.env[model._name].fields_get();
        const base = posFields.length ? posFields : Object.keys(allFields);

        if (!base.includes("id")) {
            base.push("id");
        }

        for (const fieldName of base) {
            const field = allFields[fieldName];

            if (!field) {
                continue;
            }

            relations[model._name][fieldName] = {
                name: fieldName,
                model: model._name,
                compute: Boolean(field.compute),
                related: Boolean(field.related),
                type: field.type,
                relation: field.relation,
                inverse_name: field.inverse_fname_by_model_name?.[field.relation] || false,
            };
        }

        fields[model._name] = posFields;
    }

    return { relations, fields };
};
