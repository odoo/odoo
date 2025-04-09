export async function payOrder(selfOrder, state) {
    const presets = selfOrder.models["pos.preset"].getAll();
    const config = selfOrder.config;
    const type = config.self_ordering_mode;
    const orderingMode =
        config.use_presets && presets.length > 1
            ? selfOrder.currentOrder.preset_id?.service_at
            : config.self_ordering_service_mode;

    if (selfOrder.rpcLoading || !selfOrder.verifyCart()) {
        return;
    }

    if (!selfOrder.currentOrder.presetRequirementsFilled && orderingMode !== "table") {
        state.fillInformations = true;
        return;
    }

    if (
        type === "mobile" &&
        orderingMode === "table" &&
        !selfOrder.currentTable &&
        selfOrder.config.module_pos_restaurant
    ) {
        state.selectTable = true;
        return;
    } else {
        selfOrder.currentOrder.table_id = selfOrder.currentTable;
    }

    selfOrder.rpcLoading = true;
    await selfOrder.confirmOrder();
    selfOrder.rpcLoading = false;
}
