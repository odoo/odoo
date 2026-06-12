import { Component, onWillStart, onWillUpdateProps, props, proxy, t } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";
import { KeepLast } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { hasTouch } from "@web/core/browser/feature_detection";
import { ModelFieldSelectorPopover } from "./model_field_selector_popover";

export class ModelFieldSelector extends Component {
    static template = "web._ModelFieldSelector";
    static components = {
        Popover: ModelFieldSelectorPopover,
    };
    props = props({
        resModel: t.string(),
        path: t.any().optional(),
        allowEmpty: t.boolean().optional(false),
        readonly: t.boolean().optional(true),
        readProperty: t.boolean().optional(),
        showSearchInput: t.boolean().optional(true),
        isDebugMode: t.boolean().optional(false),
        update: t.function().optional(() => () => {}),
        filter: t.function().optional(),
        sort: t.function().optional(),
        followRelation: t.or([t.boolean(), t.function()]).optional(true),
        showDebugInput: t.boolean().optional(),
    });

    setup() {
        this.fieldService = useService("field");
        this.popover = usePopover(this.constructor.components.Popover, {
            popoverClass: "o_popover_field_selector",
            onClose: async () => {
                if (this.newPath !== null) {
                    const fieldInfo = await this.fieldService.loadFieldInfo(
                        this.props.resModel,
                        this.newPath
                    );
                    this.props.update(this.newPath, fieldInfo);
                }
            },
            useBottomSheet: this.isBottomSheet,
        });
        this.keepLast = new KeepLast();
        this.state = proxy({ isInvalid: false, displayNames: [] });
        onWillStart(() => this.updateState(this.props));
        onWillUpdateProps((nextProps) => {
            const modelPathKeys = ["resModel", "path", "allowEmpty"];
            if (modelPathKeys.some((key) => this.props[key] !== nextProps[key])) {
                this.updateState(nextProps);
            }
        });
    }

    get isBottomSheet() {
        return hasTouch();
    }

    getPopoverProps() {
        return {
            resModel: this.props.resModel,
            path: this.props.path,
            readProperty: this.props.readProperty,
            update: (path, _fieldInfo, debug = false) => {
                this.newPath = path;
                if (!debug) {
                    this.updateState({ ...this.props, path }, true);
                }
            },
            showSearchInput: this.props.showSearchInput,
            isDebugMode: this.props.isDebugMode,
            filter: this.props.filter,
            sort: this.props.sort,
            followRelation: this.props.followRelation,
            showDebugInput: this.props.showDebugInput,
        };
    }

    openPopover(currentTarget) {
        if (this.props.readonly) {
            return;
        }
        this.newPath = null;
        this.popover.open(currentTarget, this.getPopoverProps());
    }

    async updateState(params, isConcurrent) {
        const { resModel, path, allowEmpty } = params;
        let prom = this.fieldService.loadPathDescription(resModel, path, allowEmpty);
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
        this.props.update("", { resModel: this.props.resModel, fieldDef: null });
    }
}
