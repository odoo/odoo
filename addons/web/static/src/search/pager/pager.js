/** @odoo-module **/

const { Component, useState, hooks } = owl;
const { onWillUnmount, onMounted, useComponent } = hooks;

export class Pager extends Component {
    static template = "web.NewPager";
    static props = ["current", "size", "withAccessKey?"];

    setup() {
        this.state = useState({ editing: false, disabled: false });
    }

    get value() {
        return this.props.current;
    }

    _changeSelection(delta) {
        let next = this.props.current + delta;
        if (next > this.props.size) {
            next = 1;
        }
        if (next < 0) {
            next = this.props.size;
        }
        if (next !== this.props.current) {
            this.trigger("page-update", {
                current: next
            });
        }
    }

    disable() {
        this.state.disabled = true;
    }

    enable() {
        this.state.disabled = false;
    }

    _onEdit() {}
}

export function usePager(model, initialResId, resIds) {
    let currentResId = initialResId;
    const size = resIds ? resIds.length : 1;
    const page = {
        current: null,
        size
    };

    updatePager(); // initial computation

    function updatePager() {
        const current = resIds ? resIds.indexOf(currentResId) + 1 : 1;
        page.current = current;
    }

    const component = useComponent();

    model.on("update", component, () => {
        currentResId = model.root.resId;
        updatePager();
    });
    onMounted(() => {
        component.el.addEventListener("page-update", onPageChange);
    });

    onWillUnmount(() => {
        component.el.removeEventListener("page-update", onPageChange);
        model.off("update", component);
    });

    async function onPageChange(ev) {
        ev.stopPropagation();
        if (!resIds) {
            return;
        }
        const pagerComp = ev.originalComponent;
        pagerComp.disable();
        let pager = ev.detail;
        let nextId = resIds[pager.current - 1];
        await model.loadRecord({ resId: nextId });
        pagerComp.enable();
    }

    return page;
}
