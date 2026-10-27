/* global owl */

import Store from "../store.js";

const { usePlugin } = owl;

export default function useStore() {
    return usePlugin(Store);
}
