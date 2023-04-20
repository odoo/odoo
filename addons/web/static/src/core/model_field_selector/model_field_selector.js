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
        readonly: { type: Boolean, optional: true },
        showSearchInput: { type: Boolean, optional: true },
        isDebugMode: { type: Boolean, optional: true },
        update: { type: Function, optional: true },
        filter: { type: Function, optional: true },
        followRelations: { type: Boolean, optional: true },
    };
    static defaultProps = {
        readonly: true,
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
                if (this.newPath) {
                    const fieldInfo = await loadFieldInfo(this.props.resModel, this.newPath);
                    this.props.update(this.newPath, fieldInfo);
                }
            },
        });
        this.keepLast = new KeepLast();
        this.state = useState({ isInvalid: false, displayNames: [] });
        onWillStart(() => this.updateState(this.props.resModel, this.props.path));
        onWillUpdateProps((nextProps) => this.updateState(nextProps.resModel, nextProps.path));
    }

    openPopover(currentTarget) {
        if (this.props.readonly) {
            return;
        }
        this.newPath = null;
        this.popover.open(currentTarget, {
            resModel: this.props.resModel,
            path: this.props.path,
            update: (path) => {
                this.newPath = path;
                this.updateState(this.props.resModel, path, true);
            },
            showSearchInput: this.props.showSearchInput,
            isDebugMode: this.props.isDebugMode,
            filter: this.props.filter,
            followRelations: this.props.followRelations,
        });
    }

    async updateState(resModel, path, isConcurrent) {
        let prom = this.loadPathDescription(resModel, path);
        if (isConcurrent) {
            prom = this.keepLast.add(prom);
        }
        const state = await prom;
        Object.assign(this.state, state);
    }
}
