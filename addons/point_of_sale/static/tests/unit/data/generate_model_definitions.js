import { defineModels, onRpc } from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { ResourceCalendar } from "./resource_calendar.data";
import { AccountMove } from "./account_move.data";
import { PosSession } from "./pos_session.data";
import { PosConfig } from "./pos_config.data";
import { PosPreset } from "./pos_preset.data";
import { ResourceCalendarAttendance } from "./resource_calendar_attendance";
import { PosOrder } from "./pos_order.data";
import { PosOrderLine } from "./pos_order_line.data";
import { PosPackOperationLot } from "./pos_pack_operation_lot.data";
import { PosPayment } from "./pos_payment.data";
import { PosPaymentMethod } from "./pos_payment_method.data";
import { PosPrinter } from "./pos_printer.data";
import { PosCategory } from "./pos_category.data";
import { PosBill } from "./pos_bill.data";
import { ResCompany } from "./res_company.data";
import { AccountTax } from "./account_tax.data";
import { AccountTaxGroup } from "./account_tax_group.data";
import { ProductTemplate } from "./product_template.data";
import { ProductProduct } from "./product_product.data";
import { ProductAttribute } from "./product_attribute.data";
import { ProductAttributeCustomValue } from "./product_attribute_custom_value.data";
import { ProductTemplateAttributeLine } from "./product_template_attribute_line.data";
import { ProductTemplateAttributeValue } from "./product_template_attribute_value.data";
import { ProductTemplateAttributeExclusion } from "./product_template_attribute_exclusion.data";
import { ProductCombo } from "./product_combo.data";
import { ProductComboItem } from "./product_combo_item.data";
import { ResUsers } from "./res_users.data";
import { ResPartner } from "./res_partner.data";
import { ProductUom } from "./product_uom.data";
import { DecimalPrecision } from "./decimal_precision.data";
import { UomUom } from "./uom_uom.data";
import { ResCountry } from "./res_country.data";
import { ResCountryState } from "./res_country_state.data";
import { ResLang } from "./res_lang.data";
import { ProductCategory } from "./product_category.data";
import { ProductPricelist } from "./product_pricelist.data";
import { ProductPricelistItem } from "./product_pricelist_item.data";
import { AccountCashRounding } from "./account_cash_rounding.data";
import { AccountFiscalPosition } from "./account_fiscal_position.data";
import { StockPickingType } from "./stock_picking_type.data";
import { ResCurrency } from "./res_currency.data";
import { PosNote } from "./pos_note.data";
import { ProductTag } from "./product_tag.data";
import { IrModuleModule } from "./ir_module_module.data";
import { AccountJournal } from "./account_journal.data";
import { IrSequence } from "./ir_sequence.data";
import { StockWarehouse } from "./stock_warehouse.data";
import { StockRoute } from "./stock_route.data";
import { BarcodeNomenclature } from "./barcode_nomenclature.data";
import { ProductAttributeValue } from "./product_attribute_value.data";

export const hootPosModels = [
    ResCountry,
    ResCountryState,
    ResCurrency,
    ResCompany,
    ResPartner,
    ResUsers,
    ResLang,
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
    AccountTax,
    AccountTaxGroup,
    AccountMove,
    ProductCategory,
    ProductTemplate,
    ProductProduct,
    ProductAttribute,
    ProductAttributeValue,
    ProductAttributeCustomValue,
    ProductTemplateAttributeLine,
    ProductTemplateAttributeValue,
    ProductTemplateAttributeExclusion,
    ProductCombo,
    ProductComboItem,
    ProductUom,
    ProductTag,
    ProductPricelist,
    ProductPricelistItem,
    DecimalPrecision,
    StockWarehouse,
    StockRoute,
    UomUom,
    AccountCashRounding,
    AccountFiscalPosition,
    StockPickingType,
    IrSequence,
    PosNote,
    IrModuleModule,
    AccountJournal,
    ResourceCalendar,
    BarcodeNomenclature,
];

export const definePosModels = () => {
    const posModelNames = hootPosModels.map((modelClass) => modelClass.prototype.constructor._name);
    const modelsFromMail = Object.values(mailModels).filter(
        (modelClass) => !posModelNames.includes(modelClass.prototype.constructor._name)
    );
    onRpc("/pos/ping", () => {});
    defineModels([...modelsFromMail, ...hootPosModels]);
};
