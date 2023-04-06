/** @odoo-module **/

import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { KeepLast } from "@web/core/utils/concurrency";
import { ModelFieldSelectorPopover } from "./model_field_selector_popover";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";

export async function loadFieldInfo(fieldService, resModel, path) {
    if (typeof path !== "string" || !path) {
        return { resModel, fieldDef: null };
    }
    const { isInvalid, names, modelsInfo } = await fieldService.loadPath(resModel, path);
    if (isInvalid) {
        return { resModel, fieldDef: null };
    }
    const name = names.at(-1);
    const modelInfo = modelsInfo.at(-1);
    return { resModel: modelInfo.resModel, fieldDef: modelInfo.fieldDefs[name] };
}

function makeString(value) {
    return String(value ?? "-");
}

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
        this.popover = usePopover(this.constructor.components.Popover, {
            popoverClass: "o_popover_field_selector",
            onClose: async () => {
                if (this.newPath) {
                    const fieldInfo = await loadFieldInfo(
                        this.fieldService,
                        this.props.resModel,
                        this.newPath
                    );
                    this.props.update(this.newPath, fieldInfo);
                }
            },
        });
        this.keepLast = new KeepLast();
        this.fieldService = useService("field");
        this.state = useState({
            isInvalid: false,
            displayNames: [],
        });
        onWillStart(() => this.updatePath(this.props.resModel, this.props.path));
        onWillUpdateProps((nextProps) => this.updatePath(nextProps.resModel, nextProps.path));
    }

    async updatePath(resModel, path, isConcurrent) {
        let prom = this.loadPath(resModel, path);
        if (isConcurrent) {
            prom = this.keepLast.add(prom);
        }
        const state = await prom;
        Object.assign(this.state, state);
    }

    async loadPath(resModel, path) {
        // the model should be checked maybe
        if ([0, 1].includes(path)) {
            return { isInvalid: false, displayNames: [makeString(path)] };
        }
        if (typeof path !== "string" || !path) {
            return { isInvalid: true, displayNames: [makeString()] };
        }
        const { isInvalid, modelsInfo, names } = await this.fieldService.loadPath(resModel, path);
        const result = { isInvalid: !!isInvalid, displayNames: [] };
        for (let index = 0; index < names.length; index++) {
            const name = names[index];
            const fieldDef = modelsInfo[index]?.fieldDefs[name];
            result.displayNames.push(fieldDef?.string || makeString(name));
        }
        return result;
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
                this.updatePath(this.props.resModel, path, true);
            },
            showSearchInput: this.props.showSearchInput,
            isDebugMode: this.props.isDebugMode,
            filter: this.props.filter,
            followRelations: this.props.followRelations,
        });
    }
}
