import { useService } from "@web/core/utils/hooks";

export function useFloorPlanStore() {
    return useService("pos_floor_plan");
}
