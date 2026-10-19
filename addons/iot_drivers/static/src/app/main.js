/* global owl */

import { Homepage } from "./homepage.js";
import Store from "./store.js";

const { mount } = owl;

mount(Homepage, document.body, {
    plugins: [Store],
    dev: new URLSearchParams(window.location.search).has("debug"),
});
