/** @odoo-module **/
import { useEnv, useEffect, useComponent } from "@odoo/owl";

export function useDropdownGroup() {
    const env = useEnv();

    const group = {
        isInGroup: "dropdownGroup" in env,
        get isOpen() {
            return false;
        },
    };

    if (group.isInGroup) {
        const dropdown = useComponent();
        useEffect(() => {
            env.dropdownGroup.add(dropdown.state);
            () => env.delete(dropdown.state);
        });

        Object.defineProperty(group, "isOpen", {
            get: () => [...env.dropdownGroup].some((dropdown) => dropdown.isOpen),
        });
    }

    return group;
}
