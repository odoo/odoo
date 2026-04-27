import {
    Component,
    onMounted,
    onWillUnmount,
    onWillUpdateProps,
    useExternalListener,
    useRef,
    useState,
} from "@odoo/owl";
import { components, helpers } from "@odoo/o-spreadsheet";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { browser } from "@web/core/browser/browser";

const { Section, SelectionInput } = components;
const { positionToZone, deepEquals } = helpers;

export class FieldSyncSidePanel extends Component {
    static template = "spreadsheet_sale_management.FieldSyncSidePanel";
    static components = { ModelFieldSelector, Section, SelectionInput };
    static props = {
        onCloseSidePanel: Function,
        position: Object,
        isNewlyCreate: { type: Boolean, optional: true },
    };
    static defaultProps = {
        isNewlyCreate: false,
    };

    inputRef = useRef("positionInput");

    setup() {
        this.state = useState({
            newPosition: undefined,
            updateSuccessful: false,
        });
        this.showSaved(this.props.isNewlyCreate);
        useExternalListener(
            window,
            "click",
            (ev) => {
                if (
                    ev.target !== this.inputRef.el &&
                    this.inputRef.el.value !== (this.fieldSync.indexInList + 1).toString()
                ) {
                    this.updateRecordPosition();
                }
            },
            { capture: true }
        );
        onWillUpdateProps(() => {
            if (document.activeElement !== this.inputRef.el && this.inputRef.el) {
                this.inputRef.el.value = (this.fieldSync.indexInList + 1).toString();
            }
        });
        onMounted(() => {
            if (this.inputRef.el) {
                this.inputRef.el.value = (this.fieldSync.indexInList + 1).toString();
            }
        });
        onWillUnmount(() => {
            browser.clearTimeout(this.timeoutId);
            if (
                this.fieldSync &&
                this.inputRef.el.value !== (this.fieldSync.indexInList + 1).toString()
            ) {
                this.updateRecordPosition();
            }
        });
    }

    getSaleOrderLineList() {
        return this.env.model.getters.getMainSaleOrderLineList();
    }

    get fieldSyncPositionString() {
        const position = this.state.newPosition ?? this.props.position;
        const zone = positionToZone(position);
        const sheetId = position.sheetId;
        const range = this.env.model.getters.getRangeFromZone(sheetId, zone);
        return this.env.model.getters.getRangeString(range, sheetId);
    }

    get fieldSync() {
        return this.env.model.getters.getFieldSync(this.props.position);
    }

    /**
     * Filter writable fields
     */
    filterField(field) {
        return (
            !field.readonly &&
            field.name !== "order_id" &&
            ["integer", "float", "monetary", "char", "text", "many2one", "boolean"].includes(
                field.type
            )
        );
    }

    updateRecordPosition() {
        this.updateFieldSync({ indexInList: parseInt(this.inputRef.el.value) - 1 });
    }

    updateField(fieldName) {
        this.updateFieldSync({ fieldName });
    }

    onRangeChanged([rangeString]) {
        const range = this.env.model.getters.getRangeFromSheetXC(
            this.env.model.getters.getActiveSheetId(),
            rangeString
        );
        if (rangeString && !range.invalidXc) {
            this.state.newPosition ??= {};
            this.state.newPosition.sheetId = range.sheetId;
            this.state.newPosition.col = range.zone.left;
            this.state.newPosition.row = range.zone.top;
        }
    }

    onRangeConfirmed() {
        const newPosition = this.state.newPosition;
        if (!newPosition || deepEquals(newPosition, this.props.position)) {
            return;
        }
        this.updateFieldSync(newPosition);
        this.env.model.dispatch("DELETE_FIELD_SYNCS", {
            sheetId: this.props.position.sheetId,
            zone: positionToZone(this.props.position),
        });
        this.env.model.selection.selectCell(newPosition.col, newPosition.row);
        this.env.openSidePanel("FieldSyncSidePanel");
    }

    updateFieldSync(partialFieldSync) {
        const { sheetId, col, row } = this.props.position;
        const result = this.env.model.dispatch("ADD_FIELD_SYNC", {
            sheetId,
            col,
            row,
            listId: this.fieldSync.listId,
            ...this.fieldSync,
            ...partialFieldSync,
        });
        this.showSaved(result.isSuccessful);
    }

    showSaved(isDisplayed) {
        this.state.updateSuccessful = isDisplayed;
        browser.clearTimeout(this.timeoutId);
        this.timeoutId = browser.setTimeout(() => {
            this.state.updateSuccessful = false;
        }, 1500);
    }
}
