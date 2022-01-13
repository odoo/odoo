(() => {
    /**
     * This file converts the imports of Owl variables from v1 to v2
     *
     * In the previous version: imports were grouped in subkeys under the
     * global `owl` object. In the newer, all imports are top-level.
     *
     * Any call to the previous subkeys will throw an error to help
     * devs adapt to the new system.
     */

    // These are the old subkeys used to group exports
    const ROOT_KEYS = ["core", "router", "utils", "tags", "misc", "hooks"];

    for (const key of ROOT_KEYS) {
        if (!Object.getOwnPropertyDescriptor(owl, key).value) {
            // This means that the key has already been transformed
            continue;
        }
        for (const subKey in owl[key]) {
            owl[subKey] = owl[key][subKey];
        }
        // TODO: uncomment the code below as soon as o_spreadsheet ugprades to Owl v2
        // delete owl[key];
        // Object.defineProperty(owl, key, {
        //     get() {
        //         throw new Error(
        //             `Deprecated Owl import: ${key}. All properties under this key are now directly available from the global 'owl' object.`
        //         );
        //     },
        //     set() {},
        // });
    }
})();
