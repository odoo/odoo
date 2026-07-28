/* global owl */

import { Homepage } from "./Homepage.js";
import Store from "./store.js";

const { mount, reactive } = owl;

function createStore() {
    return reactive(new Store());
}

mount(Homepage, document.body, {
    env: {
        store: createStore(),
    },
});
