import { useEffect } from "@odoo/owl";

export function useDeferEffect(effect, computeDepedencies, iteration = 1) {
    useEffect(() => {
        if (iteration > 0) {
            iteration--;
            return () => {};
        }
        return effect();
    }, computeDepedencies);
}
