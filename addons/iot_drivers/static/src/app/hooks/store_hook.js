/* global owl */

import Store from "../store.js";

const { plugin } = owl;

export default function useStore() {
    return plugin(Store);
}
