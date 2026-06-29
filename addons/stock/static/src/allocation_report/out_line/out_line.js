import { computed, props, signal, types, Component } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { formatDate, parseDate, serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
const { DateTime } = luxon;

export class OutLine extends Component {
    static template = "stock.AllocationReport.OutLine";
    props = props({
        allocateQuantity: types.signal(types.number()),
        availableQuantity: types.number(),
        isReserved: types.signal(types.boolean()),
        isSmall: types.boolean().optional(),
        moves: types.array(),
        productUom: types.object(),
        reservedQuantity: types.signal(types.number()),
        updateMoveReservation: types.function(),
    })
    static components = {
        CheckBox,
    }

    favorite = computed(() => this.props.moves.some(move => move.priority == 1))
    date = computed(() => this.props.moves[0].date)
    isLate = computed(() => this.date() < serializeDateTime(DateTime.now()))
    demandQuantity = computed(() => this.props.moves.reduce((v, mv) => v + mv.quantity, 0))

    setup() {
        const move = this.props.moves[0];
        this.partner = move.partner;
        this.picking = move.picking;
        this.source = move.source;
        this.uom = move.uom;
        this.onGoingJob = signal(false); // To avoid multi-click on reservation widget.
    }

    get quantityCSSClass() {
        if (this.props.reservedQuantity()) {
            return this.props.reservedQuantity() >= this.demandQuantity() ? "text-success" : "text-warning";
        } else if (this.props.allocateQuantity() && this.props.allocateQuantity() >= this.demandQuantity()) {
            return "";
        }
        return "text-danger";
    }

    get quantityToDisplay() {
        return this.props.reservedQuantity() || this.props.allocateQuantity();
    }

    getCheckBoxProps() {
        let disabled = this.props.isReserved() ? false : !this.props.availableQuantity;
        if (this.props.moves.some(move => ["cancel", "done"].includes(move.state))) {
            disabled = true;
        }
        return {
            disabled: this.onGoingJob() || disabled,
            id: String(this.props.id),
            value: this.props.isReserved(),
            name: _t("Reserved"),
            className: "o_field_boolean o_boolean_toggle form-switch m-auto",
            onChange: async (value) => {
                this.onGoingJob.set(true);
                await this.props.updateMoveReservation(value, this.props);
                this.onGoingJob.set(false);
            },
        }
    }

    displayDate(date) {
        return formatDate(parseDate(date));
    }

    async onPrintLabels() {
        if (this.props.reservedQuantity()) {
            const docids = this.props.moves.map((move) => move.id)
            const movesQty = this.props.moves.map((move) => move.is_reserved ? move.quantity : 0);
            await this.env.bus.trigger("print_labels", { docids, movesQty });
        }
    }

    dateColor() {
        const today = serializeDate(DateTime.now());
        const scheduledDate = serializeDate(parseDate(this.date()));
        if (today === scheduledDate) {
            return "text-warning";
        }
        return today > scheduledDate ? "text-danger" : "";
    }
}
