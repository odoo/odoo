/** @odoo-module **/

import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { KeepLast } from "@web/core/utils/concurrency";
import { ModelFieldSelectorPopover } from "./model_field_selector_popover";
import { useLoadFieldInfo, useLoadPathDescription } from "./utils";
import { usePopover } from "@web/core/popover/popover_hook";

export class ModelFieldSelector extends Component {
    static template = "web._ModelFieldSelector";
    static components = {
        Popover: ModelFieldSelectorPopover,
    };
    static props = {
        resModel: String,
        path: { optional: true },
        allowEmpty: { type: Boolean, optional: true },
        readonly: { type: Boolean, optional: true },
        showSearchInput: { type: Boolean, optional: true },
        isDebugMode: { type: Boolean, optional: true },
        update: { type: Function, optional: true },
        filter: { type: Function, optional: true },
        followRelations: { type: Boolean, optional: true },
        showDebugInput: { type: Boolean, optional: true },
    };
    static defaultProps = {
        readonly: true,
        allowEmpty: false,
        isDebugMode: false,
        showSearchInput: true,
        update: () => {},
        followRelations: true,
    };

    setup() {
        this.loadPathDescription = useLoadPathDescription();
        const loadFieldInfo = useLoadFieldInfo();
        this.popover = usePopover(this.constructor.components.Popover, {
            popoverClass: "o_popover_field_selector",
            onClose: async () => {
                if (this.newPath !== null) {
                    const fieldInfo = await loadFieldInfo(this.props.resModel, this.newPath);
                    this.props.update(this.newPath, fieldInfo);
                }
            },
        });
        this.keepLast = new KeepLast();
        this.state = useState({ isInvalid: false, displayNames: [] });
        onWillStart(() => this.updateState(this.props));
        onWillUpdateProps((nextProps) => this.updateState(nextProps));
    }

    openPopover(currentTarget) {
        if (this.props.readonly) {
            return;
        }
        this.newPath = null;
        this.popover.open(currentTarget, {
            resModel: this.props.resModel,
            path: this.props.path,
            update: (path, debug = false) => {
                this.newPath = path;
                if (!debug) {
                    this.updateState({ ...this.props, path }, true);
                }
            },
            showSearchInput: this.props.showSearchInput,
            isDebugMode: this.props.isDebugMode,
            filter: this.props.filter,
            followRelations: this.props.followRelations,
            showDebugInput: this.props.showDebugInput,
        });
    }

    async updateState(params, isConcurrent) {
        const { resModel, path, allowEmpty } = params;
        let prom = this.loadPathDescription(resModel, path, allowEmpty);
        if (isConcurrent) {
            prom = this.keepLast.add(prom);
        }
        const state = await prom;
        Object.assign(this.state, state);
    }

    clear() {
        if (this.popover.isOpen) {
            this.newPath = "";
            this.popover.close();
            return;
        }
        this.props.update("", { resModel: this.props.resModel, fieodDef: null });
    }
}
