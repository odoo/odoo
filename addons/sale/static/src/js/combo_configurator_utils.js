import { rpc } from "@web/core/network/rpc";
import { serializeDateTime } from "@web/core/l10n/dates";
import { uuid } from "@web/core/utils/strings";
import { ComboConfiguratorDialog } from "@sale/js/combo_configurator_dialog/combo_configurator_dialog";
import { ProductCombo } from "@sale/js/models/product_combo";
import { clearSelectedComboItems, serializeComboItem } from "@sale/js/sale_utils";

/**
 * Fetch the combo configurator data for the provided combo line, and open the combo
 * configurator dialog. If every combo already has a preselected item, the dialog is
 * skipped and the line is saved directly.
 *
 * @param {Object} params
 * @param {Object} params.dialog The dialog service.
 * @param {Object} params.comboLineRecord The sale order line record configuring the combo.
 * @param {Boolean} params.edit Whether an existing combo line is being edited.
 * @param {Object[]} [params.selectedComboItems] The currently selected combo items (edit only).
 */
export async function openComboConfigurator({
    dialog,
    comboLineRecord,
    edit = false,
    selectedComboItems = [],
    additionalRpcParams = {},
    additionalDialogProps = {},
    onSave, // optional (comboProductData, selectedComboItems, remainingData) => void
}) {
    const saleOrder = comboLineRecord.model.root.data;

    const { combos, ...remainingData } = await rpc("/sale/combo_configurator/get_data", {
        product_tmpl_id: comboLineRecord.data.product_template_id.id,
        currency_id: comboLineRecord.data.currency_id.id,
        quantity: comboLineRecord.data.product_uom_qty,
        date: serializeDateTime(saleOrder.date_order),
        company_id: saleOrder.company_id.id,
        pricelist_id: saleOrder.pricelist_id?.id,
        ...(edit ? { selected_combo_items: selectedComboItems } : {}),
        ...additionalRpcParams,
    });

    const comboChoices = combos.map(combo => new ProductCombo(combo));
    const save = async (comboProductData, selectedItems) => {
        await saveComboLine(comboLineRecord, comboProductData, selectedItems, edit);
        await onSave?.(comboProductData, selectedItems, remainingData);
    };
    const discard = () => saleOrder.order_line.delete(comboLineRecord);

    if (!edit) {
        const preselectedComboItems = comboChoices
            .map(combo => combo.preselectedComboItem)
            .filter(Boolean);
        if (preselectedComboItems.length === comboChoices.length) {
            return save({ quantity: remainingData.quantity }, preselectedComboItems);
        }
    }

    dialog.add(ComboConfiguratorDialog, {
        combos: comboChoices,
        ...remainingData,
        company_id: saleOrder.company_id.id,
        pricelist_id: saleOrder.pricelist_id?.id,
        date: serializeDateTime(saleOrder.date_order),
        edit,
        save,
        discard,
        ...(edit && {
            deleteRecord: async () => {
                await clearSelectedComboItems(comboLineRecord);
                await saleOrder.order_line.delete(comboLineRecord);
            },
        }),
        ...additionalDialogProps,
    });
}

async function saveComboLine(comboLineRecord, comboProductData, selectedComboItems, edit) {
    const saleOrder = comboLineRecord.model.root.data;
    saleOrder.order_line.leaveEditMode();

    const comboLineValues = {
        product_uom_qty: comboProductData.quantity,
        selected_combo_items: JSON.stringify(selectedComboItems.map(serializeComboItem)),
    };
    if (!edit) {
        comboLineValues.virtual_id = uuid();
    }
    await comboLineRecord.update(comboLineValues);
    await saleOrder.order_line._sort();
}
