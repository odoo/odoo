/** @odoo-module */

import {
    Component,
    onMounted,
    reactive,
    useExternalListener,
    useRef,
    useState,
    xml,
} from "@odoo/owl";
import { refresh } from "../core/url";
import { MockMath, generateSeed, internalRandom } from "../mock/math";
import { storage } from "../hoot_utils";
import { HootCopyButton } from "./hoot_copy_button";

/**
 * @typedef {"dark" | "light"} ColorScheme
 *
 * @typedef {{}} HootConfigDropdownProps
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { Object, document, matchMedia } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {string} storageKey
 */
const makeColorSchemeStore = (storageKey) => {
    const toggle = () => {
        color.scheme = COLOR_SCHEMES.at(COLOR_SCHEMES.indexOf(color.scheme) - 1);
        set(storageKey, color.scheme);
    };

    const updateClassNames = () => {
        const { classList } = document.documentElement;
        classList.remove(...Object.values(colorMap));
        classList.add(colorMap[color.scheme]);
    };

    const { get, set } = storage("local");

    /** @type {ColorScheme} */
    let defaultScheme = get(storageKey);
    if (!COLOR_SCHEMES.includes(defaultScheme)) {
        defaultScheme = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
        set(storageKey, defaultScheme);
    }

    const colorMap = Object.fromEntries(COLOR_SCHEMES.map((cls) => [cls, `hoot-${cls}`]));
    const color = reactive(
        {
            scheme: defaultScheme,
            toggle,
        },
        updateClassNames
    );

    onMounted(updateClassNames);

    return useState(color);
};

/** @type {ColorScheme[]} */
const COLOR_SCHEMES = ["dark", "light"];

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/** @extends Component<HootConfigDropdownProps, import("../hoot").Environment> */
export class HootConfigDropdown extends Component {
    static components = { HootCopyButton };

    static props = {};

    static template = xml`
        <div class="hoot-config dropdown" t-ref="root">
            <button t-ref="toggler" class="hoot-btn hoot-btn-primary p-2 h-100" title="Configuration">
                <i class="fa fa-cog" />
            </button>
            <t t-if="state.open">
                <form
                    class="hoot-dropdown position-absolute d-flex flex-column end-0 px-2 py-3 shadow rounded"
                    t-on-submit.prevent="refresh"
                >
                    <label
                        class="hoot-checkbox hoot-dropdown-line p-1"
                        title="Display the tests that passed in the list of test results"
                    >
                        <input type="checkbox" t-model="config.showpassed" />
                        <span>Show passed tests</span>
                    </label>
                    <label
                        class="hoot-checkbox hoot-dropdown-line p-1"
                        title="Show all tests that have been skipped"
                    >
                        <input type="checkbox" t-model="config.showskipped" />
                        <span>Show skipped tests</span>
                    </label>
                    <label
                        class="hoot-checkbox hoot-dropdown-line p-1"
                        title="Shuffles tests and suites order within their parent suite"
                    >
                        <input
                            type="checkbox"
                            t-att-checked="config.random"
                            t-on-change="onRandomChange"
                        />
                        <span>Random order</span>
                    </label>
                    <t t-if="config.random">
                        <small class="d-flex p-1 pt-0 gap-1">
                            <span class="hoot-text-muted text-nowrap ms-1">Seed:</span>
                            <input
                                class="hoot-border-primary px-1 border-top-0 border-start-0 border-end-0 w-100"
                                t-model.number="config.random"
                            />
                            <button
                                type="button"
                                title="Generate new random seed"
                                t-on-click="resetSeed"
                            >
                                <i class="fa fa-repeat" />
                            </button>
                            <HootCopyButton text="config.random.toString()" />
                        </small>
                    </t>
                    <label
                        class="hoot-checkbox hoot-dropdown-line p-1"
                        title="Re-run current tests in headless mode (no UI)"
                    >
                        <input
                            type="checkbox"
                            t-model="config.headless"
                        />
                        <span>Headless</span>
                    </label>
                    <label
                        class="hoot-checkbox hoot-dropdown-line p-1"
                        title="Re-run current tests and abort after a given amount of failed tests"
                    >
                        <input
                            type="checkbox"
                            t-att-checked="config.bail"
                            t-on-change="onBailChange"
                        />
                        <span>Bail</span>
                    </label>
                    <t t-if="config.bail">
                        <small class="d-flex p-1 pt-0 gap-1">
                            <span class="hoot-text-muted text-nowrap ms-1">Failed tests:</span>
                            <input
                                type="number"
                                class="hoot-border-primary px-1 border-top-0 border-start-0 border-end-0"
                                t-model.number="config.bail"
                            />
                        </small>
                    </t>
                    <label
                        class="hoot-checkbox hoot-dropdown-line p-1"
                        title="Re-run current tests without catching any errors"
                    >
                        <input
                            type="checkbox"
                            t-model="config.notrycatch"
                        />
                        <span>No try/catch</span>
                    </label>
                    <label
                        class="hoot-checkbox hoot-dropdown-line p-1"
                        title="Disables the checks after tests such as remaining DOM elements, listeners, etc."
                    >
                        <input
                            type="checkbox"
                            t-model="config.nowatcher"
                        />
                        <span>No watcher</span>
                    </label>
                    <button
                        type="button"
                        class="hoot-dropdown-line p-1"
                        title="Toggle the color scheme of the UI"
                        t-on-click="color.toggle"
                    >
                        <i t-attf-class="fa fa-{{ color.scheme === 'light' ? 'moon' : 'sun' }}-o" />
                        Color scheme
                    </button>
                    <button class="hoot-btn hoot-btn-primary mt-1 p-1">
                        Apply and refresh
                    </button>
                </form>
            </t>
        </div>
    `;

    refresh = refresh;

    setup() {
        this.rootRef = useRef("root");
        this.togglerRef = useRef("toggler");

        this.color = useState(makeColorSchemeStore("color-scheme"));
        this.config = useState(this.env.runner.config);
        this.state = useState({ open: false });

        useExternalListener(window, "keydown", (ev) => {
            if (this.state.open && ev.key === "Escape") {
                ev.preventDefault();
                this.state.open = false;
            }
        });
        useExternalListener(window, "click", (ev) => {
            if (!this.rootRef.el?.contains(ev.target)) {
                this.state.open = false;
            } else if (this.togglerRef.el?.contains(ev.target)) {
                this.state.open = !this.state.open;
            }
        });
    }

    onBailChange(ev) {
        this.config.bail = ev.target.checked ? 1 : 0;
    }

    onRandomChange(ev) {
        if (ev.target.checked) {
            this.resetSeed();
        } else {
            this.config.random = 0;
        }
    }

    resetSeed() {
        this.config.random = generateSeed();
        internalRandom.seed = this.config.random;
        MockMath.random.seed = this.config.random;
    }
}
