/** @odoo-module **/

import {
    Component,
    onMounted,
    onWillDestroy,
    onWillUpdateProps,
    useChildSubEnv,
    useState,
} from "@odoo/owl";
import { nextId, sanitizeIdFragment } from "@odx_owl/core/utils/ids";
import { cn } from "@odx_owl/core/utils/cn";
import { isRtlDirection, resolveDirection } from "@odx_owl/core/utils/direction";

function moveFocus(tabs, nextIndex, tabsApi) {
    const target = tabs[nextIndex];
    if (!target) {
        return;
    }
    target.focus();
    if (tabsApi.activationMode !== "manual") {
        target.click();
    }
}

function sortRegisteredTriggers(items = []) {
    return [...items].sort((left, right) => left.order - right.order);
}

export class Tabs extends Component {
    static template = "odx_owl.Tabs";
    static props = {
        activationMode: { type: String, optional: true },
        className: { type: String, optional: true },
        defaultValue: { optional: true },
        dir: { type: String, optional: true },
        loop: { type: Boolean, optional: true },
        onValueChange: { type: Function, optional: true },
        orientation: { type: String, optional: true },
        slots: { type: Object, optional: true },
        value: { optional: true, validate: () => true },
    };
    static defaultProps = {
        activationMode: "automatic",
        className: "",
        loop: true,
        orientation: "horizontal",
    };

    setup() {
        const self = this;
        this.state = useState({
            baseId: nextId("odx-tabs"),
            registeredTriggers: [],
            registryOrder: 0,
            tabStopValue: this.props.value ?? this.props.defaultValue ?? null,
            value: this.props.value ?? this.props.defaultValue ?? null,
        });
        useChildSubEnv({
            odxTabs: {
                get activationMode() {
                    return self.props.activationMode;
                },
                get dir() {
                    return self.direction;
                },
                get loop() {
                    return self.props.loop;
                },
                get orientation() {
                    return self.props.orientation;
                },
                getTabIndex: (value) => self.getTabIndex(value),
                get value() {
                    return self.props.value ?? self.state.value;
                },
                registerTrigger: (token, trigger) => self.registerTrigger(token, trigger),
                setTabStop: (value) => self.setTabStop(value),
                setValue: (value) => this.setValue(value),
                getTriggerId: (value) => `${this.state.baseId}-trigger-${sanitizeIdFragment(value)}`,
                getPanelId: (value) => `${this.state.baseId}-panel-${sanitizeIdFragment(value)}`,
                isActive: (value) => this.isActive(value),
                unregisterTrigger: (token) => self.unregisterTrigger(token),
            },
        });

        onMounted(() => {
            this.syncTabStop(true);
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.value !== undefined) {
                this.state.value = nextProps.value;
            }
            this.syncTabStop(nextProps.value !== undefined);
        });
    }

    get classes() {
        return cn("odx-tabs", this.props.className);
    }

    get direction() {
        return resolveDirection(this.props.dir);
    }

    get registeredTriggers() {
        return sortRegisteredTriggers(this.state.registeredTriggers);
    }

    get enabledTriggers() {
        return this.registeredTriggers.filter((trigger) => !trigger.disabled);
    }

    get defaultTabStopValue() {
        const activeTrigger = this.enabledTriggers.find((trigger) => this.isActive(trigger.value));
        return activeTrigger?.value ?? this.enabledTriggers[0]?.value ?? null;
    }

    isActive(value) {
        return (this.props.value ?? this.state.value) === value;
    }

    registerTrigger(token, trigger) {
        const existingIndex = this.state.registeredTriggers.findIndex((entry) => entry.token === token);
        const existingTrigger =
            existingIndex === -1 ? null : this.state.registeredTriggers[existingIndex];
        const nextTrigger = {
            ...trigger,
            order:
                existingIndex === -1
                    ? this.state.registryOrder++
                    : existingTrigger.order,
            token,
        };
        if (
            existingTrigger &&
            existingTrigger.disabled === nextTrigger.disabled &&
            existingTrigger.value === nextTrigger.value
        ) {
            return;
        }
        if (existingIndex === -1) {
            this.state.registeredTriggers.push(nextTrigger);
        } else {
            this.state.registeredTriggers.splice(existingIndex, 1, nextTrigger);
        }
        this.syncTabStop();
    }

    unregisterTrigger(token) {
        const existingIndex = this.state.registeredTriggers.findIndex((entry) => entry.token === token);
        if (existingIndex !== -1) {
            this.state.registeredTriggers.splice(existingIndex, 1);
        }
        this.syncTabStop();
    }

    syncTabStop(preferSelection = false) {
        const enabledTriggers = this.enabledTriggers;
        if (!enabledTriggers.length) {
            this.state.tabStopValue = null;
            return;
        }
        const currentTabStop = enabledTriggers.find((trigger) => trigger.value === this.state.tabStopValue);
        if (currentTabStop && !preferSelection) {
            return;
        }
        this.state.tabStopValue = this.defaultTabStopValue;
    }

    setTabStop(value) {
        if (this.enabledTriggers.some((trigger) => trigger.value === value)) {
            this.state.tabStopValue = value;
        }
    }

    getTabIndex(value) {
        return value === (this.state.tabStopValue ?? this.defaultTabStopValue) ? 0 : -1;
    }

    setValue(value) {
        if (this.props.value === undefined) {
            this.state.value = value;
        }
        this.setTabStop(value);
        this.props.onValueChange?.(value);
    }
}

export class TabsList extends Component {
    static template = "odx_owl.TabsList";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-tabs__list", this.props.className);
    }

    onKeydown(ev) {
        const horizontal = this.env.odxTabs.orientation !== "vertical";
        const triggers = [...ev.currentTarget.querySelectorAll('[role="tab"]:not([disabled])')];
        const currentIndex = triggers.indexOf(document.activeElement);
        if (!triggers.length || currentIndex === -1) {
            return;
        }
        const key = ev.key;
        if ((horizontal && !["ArrowRight", "ArrowLeft", "Home", "End"].includes(key)) ||
            (!horizontal && !["ArrowDown", "ArrowUp", "Home", "End"].includes(key))) {
            return;
        }
        ev.preventDefault();
        if (key === "Home") {
            moveFocus(triggers, 0, this.env.odxTabs);
            return;
        }
        if (key === "End") {
            moveFocus(triggers, triggers.length - 1, this.env.odxTabs);
            return;
        }
        const isRtl = horizontal && isRtlDirection(this.env.odxTabs.dir);
        const direction =
            key === "ArrowDown"
                ? 1
                : key === "ArrowUp"
                  ? -1
                  : key === "ArrowRight"
                    ? isRtl
                        ? -1
                        : 1
                    : isRtl
                      ? 1
                      : -1;
        const nextIndex = currentIndex + direction;
        if (nextIndex < 0 || nextIndex >= triggers.length) {
            if (!this.env.odxTabs.loop) {
                return;
            }
            moveFocus(
                triggers,
                (nextIndex + triggers.length) % triggers.length,
                this.env.odxTabs
            );
            return;
        }
        moveFocus(triggers, nextIndex, this.env.odxTabs);
    }
}

export class TabsTrigger extends Component {
    static template = "odx_owl.TabsTrigger";
    static props = {
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        value: { validate: () => true },
    };
    static defaultProps = {
        className: "",
        disabled: false,
    };

    setup() {
        this.token = nextId("odx-tabs-trigger");

        onMounted(() => {
            this.register(this.props);
        });

        onWillUpdateProps((nextProps) => {
            this.register(nextProps);
        });

        onWillDestroy(() => {
            this.env.odxTabs.unregisterTrigger(this.token);
        });
    }

    get classes() {
        return cn("odx-tabs__trigger", { "odx-tabs__trigger--active": this.isActive }, this.props.className);
    }

    get isActive() {
        return this.env.odxTabs.isActive(this.props.value);
    }

    get triggerId() {
        return this.env.odxTabs.getTriggerId(this.props.value);
    }

    get panelId() {
        return this.env.odxTabs.getPanelId(this.props.value);
    }

    get orientation() {
        return this.env.odxTabs.orientation;
    }

    get tabIndex() {
        return this.props.disabled ? -1 : this.env.odxTabs.getTabIndex(this.props.value);
    }

    register(props = this.props) {
        this.env.odxTabs.registerTrigger(this.token, {
            disabled: Boolean(props.disabled),
            value: props.value,
        });
    }

    onFocus() {
        if (!this.props.disabled) {
            this.env.odxTabs.setTabStop(this.props.value);
        }
    }

    onKeydown(ev) {
        if (this.props.disabled || this.env.odxTabs.activationMode !== "manual") {
            return;
        }
        if (!["Enter", " "].includes(ev.key)) {
            return;
        }
        ev.preventDefault();
        this.select();
    }

    select() {
        if (!this.props.disabled) {
            this.env.odxTabs.setValue(this.props.value);
        }
    }
}

export class TabsContent extends Component {
    static template = "odx_owl.TabsContent";
    static props = {
        className: { type: String, optional: true },
        forceMount: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        value: { validate: () => true },
    };
    static defaultProps = {
        className: "",
        forceMount: false,
    };

    setup() {
        this.hasRendered = false;
    }

    get classes() {
        return cn("odx-tabs__content", this.props.className);
    }

    get isActive() {
        return this.env.odxTabs.isActive(this.props.value);
    }

    get triggerId() {
        return this.env.odxTabs.getTriggerId(this.props.value);
    }

    get panelId() {
        return this.env.odxTabs.getPanelId(this.props.value);
    }

    get orientation() {
        return this.env.odxTabs.orientation;
    }

    get shouldRender() {
        if (this.props.forceMount || this.isActive) {
            this.hasRendered = true;
        }
        return this.hasRendered;
    }
}
