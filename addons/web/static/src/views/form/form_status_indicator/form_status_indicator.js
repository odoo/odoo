import { Component, onWillDestroy, onWillUnmount, useEffect, useRef, useState, reactive } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";

export class FormStatusIndicator extends Component {
    static template = "web.FormStatusIndicator";
    static props = {
        model: Object,
        save: Function,
        discard: Function,
    };

    setup() {
        this.state = useState({
            displayButtons: false,
            indicatorMode: "saved",
        });
        this.fieldIsDirty = reactive({
            value: false,
        }, this.updateDisplayButtons.bind(this));
        useBus(
            this.props.model.bus,
            "FIELD_IS_DIRTY",
            (ev) => (this.fieldIsDirty.value = ev.detail)
        );
        useEffect(
            () => {
                console.log(JSON.stringify({
                    isNew: this.props.model.root.isNew,
                    indicatorMode: this.indicatorMode,
                }));
                if (!this.props.model.root.isNew && this.indicatorMode === "invalid") {
                    this.saveButton.el.setAttribute("disabled", "1");
                    console.log("Save button disabled due to invalid form");
                } else {
                    this.saveButton.el.removeAttribute("disabled");
                    console.log("Save button enabled");
                }
                console.log("attibutes:", this.saveButton.el.attributes);
            },
            () => [this.props.model.root.isValid]
        );
        onWillDestroy(() => {
            console.log("FormStatusIndicator is being destroyed");
        });
        onWillUnmount(() => {
            console.log("FormStatusIndicator is being unmounted");
        });
        this.saveButton = useRef("save");
        this.updateDisplayButtons();
    }

    updateDisplayButtons() {
        const indicatorMode = this.indicatorMode;
        if (this.state.indicatorMode !== indicatorMode) {
            this.state.indicatorMode = indicatorMode;
            console.log("Updated indicatorMode to:", indicatorMode);
        }
        const shouldDisplay = this.displayButtons;
        if (this.state.displayButtons !== shouldDisplay) {
            this.state.displayButtons = shouldDisplay;
            console.log("Updated displayButtons to:", shouldDisplay);
        }
    }

    get displayButtons() {
        const tmp = this.indicatorMode !== "saved";
        console.log("indicatorMode:", JSON.stringify({ displayButtons: tmp }));
        return tmp;
    }

    get indicatorMode() {
        if (this.props.model.root.isNew) {
            console.log(this.props.model.root.isValid ? "dirty/new" : "invalid/new");
            return this.props.model.root.isValid ? "dirty" : "invalid";
        } else if (!this.props.model.root.isValid) {
            console.log("invalid form");
            return "invalid";
        } else if (this.props.model.root.dirty || this.fieldIsDirty.value) {
            console.log("dirty: ", JSON.stringify({ dirty: this.props.model.root.dirty, fieldIsDirty: this.fieldIsDirty.value }));
            return "dirty";
        } else {
            console.log("saved");
            return "saved";
        }
    }

    async discard() {
        await this.props.discard();
    }
    async save() {
        await this.props.save();
    }
}
