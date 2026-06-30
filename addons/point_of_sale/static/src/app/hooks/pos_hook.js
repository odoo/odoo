import { useService } from "@web/core/utils/hooks";

/**
 * @returns {import("@point_of_sale/app/services/pos_store").PosStore}
 */
export function usePos() {
    return useService("pos");
}

export function usePosRouter() {
    return useService("pos_router");
}
