import {
    applyObjectPropertyDifference,
    getEmbeddedProps,
    StateChangeManager,
    useEditableDescendants,
    useEmbeddedState,
} from "@html_editor/others/embedded_component_utils";
import { Component, computed, signal, t, useProps, xml } from "@odoo/owl";

export class Counter extends Component {
    static template = xml`
        <span class="counter" t-on-click="this.increment">Counter:<t t-out="this.value()"/></span>
    `;

    value = signal(0);

    increment() {
        this.value.set(this.value() + 1);
    }
}

export const EmbeddedWrapperMixin = (editableDescendantName) =>
    class extends Component {
        static template = xml`
            <div class="${editableDescendantName}" t-ref="this.descendantRefs.${editableDescendantName}" />
        `;

        setup() {
            this.descendantRefs = useEditableDescendants().refs;
        }
    };

export class EmbeddedWrapper extends Component {
    static template = xml`
        <t>
            <div t-if="this.editableDescendants.shallow" class="shallow" t-ref="this.descendantRefs.shallow"/>
            <div t-if="!this.switch()">
                <div class="deep" t-ref="this.descendantRefs.deep"/>
            </div>
            <div t-else="">
                <div class="switched">
                    <div class="deep" t-ref="this.descendantRefs.deep"/>
                </div>
            </div>
        </t>
    `;

    switch = signal(false);

    setup() {
        const { descendants, refs } = useEditableDescendants();
        this.editableDescendants = descendants;
        this.descendantRefs = refs;
    }
}

export class OffsetCounter extends Component {
    static template = xml`
        <span class="counter" t-on-click="this.increment">Counter:<t t-out="this.counterValue()"/></span>
    `;

    props = useProps({
        host: t.object(),
    });

    value = signal(0);
    counterValue = computed(() => this.value() + this.embeddedState.baseValue);

    setup() {
        this.embeddedState = useEmbeddedState(this.props.host);
    }

    increment() {
        this.value.set(this.value() + 1);
    }
}

export const offsetCounter = {
    name: "counter",
    Component: OffsetCounter,
    getProps: (host) => ({ host }),
    getStateChangeManager: (config) =>
        new StateChangeManager(
            Object.assign(config, {
                propertyUpdater: {
                    baseValue: (state, previous, next) => {
                        const offset = next.baseValue - previous.baseValue;
                        state.baseValue += offset;
                    },
                },
            })
        ),
};

export class SavedCounter extends Component {
    static template = xml`
        <span class="counter" t-on-click="this.increment">Counter:<t t-out="this.counterValue()"/></span>
    `;

    props = useProps({
        host: t.object(),
    });

    counterValue = computed(() => this.embeddedState.value || 0);

    setup() {
        this.embeddedState = useEmbeddedState(this.props.host);
    }

    increment() {
        if (!this.embeddedState.value) {
            this.embeddedState.value = 0;
        }
        this.embeddedState.value++;
    }
}

export const savedCounter = {
    name: "counter",
    Component: SavedCounter,
    getProps: (host) => ({ host }),
    getStateChangeManager: (config) => new StateChangeManager(config),
};

export class CollaborativeObject extends Component {
    static template = xml`
        <div class="obj" t-out="this.collaborativeObject()" />
    `;

    props = useProps({
        host: t.object(),
    });

    collaborativeObject = computed(() =>
        Object.entries(this.embeddedState.obj || {})
            .map(([key, value]) => `${key}_${value}`)
            .join(",")
    );

    setup() {
        this.embeddedState = useEmbeddedState(this.props.host);
    }
}

export const collaborativeObject = {
    name: "obj",
    Component: CollaborativeObject,
    getProps: (host) => ({ host }),
    getStateChangeManager: (config) =>
        new StateChangeManager(
            Object.assign(config, {
                propertyUpdater: {
                    obj: (state, previous, next) => {
                        applyObjectPropertyDifference(state, "obj", previous.obj, next.obj);
                    },
                },
            })
        ),
};

export class NamedCounter extends Component {
    static template = xml`
        <span class="counter" t-on-click="this.increment">
            <t t-out="this.props.name" />:<t t-out="this.counterValue()" />
        </span>
    `;

    props = useProps({
        host: t.object(),
        name: t.string(),
        value: t.number(),
    });

    counterValue = computed(() => this.embeddedState.value + this.embeddedState.baseValue);

    setup() {
        this.embeddedState = useEmbeddedState(this.props.host);
    }

    increment() {
        this.embeddedState.value++;
    }
}

export const namedCounter = {
    name: "counter",
    Component: NamedCounter,
    getProps: (host) => ({
        host,
        ...getEmbeddedProps(host),
    }),
    getStateChangeManager: (config) =>
        new StateChangeManager(
            Object.assign(config, {
                propertyUpdater: {
                    baseValue: (state, previous, next) => {
                        const offset = next.baseValue - previous.baseValue;
                        state.baseValue += offset;
                    },
                },
                getEmbeddedState: (host) => {
                    const props = getEmbeddedProps(host);
                    return {
                        value: props.value,
                        baseValue: 3,
                    };
                },
                stateToEmbeddedProps: (host, state) => ({
                    ...getEmbeddedProps(host),
                    value: state.value,
                }),
            })
        ),
};

export function embedding(
    name,
    Component,
    getProps = undefined,
    { getEditableDescendants, getStateChangeManager } = {}
) {
    return {
        name,
        Component,
        ...(getProps ? { getProps } : {}),
        ...arguments[3],
    };
}
