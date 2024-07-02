import { Component } from "@odoo/owl";

export class InternalNote extends Component {
    static template = "point_of_sale.InternalNote";
    static props = {
        notes: { type: String, optional: true },
        defaultNotes: { type: Object, optional: true },
        class: { type: String, optional: true },
    };
    static defaultProps = {
        notes: "",
        class: "",
    };

    get internalNotes() {
        if (!this.props.notes) {
            return [];
        }

        const defaultNotesColors = new Map(
            this.props.defaultNotes?.map((note) => [note.name.trim(), note.color])
        );

        return this.props.notes
            .split("\n")
            .filter((note) => note.trim() !== "")
            .map((note) => ({
                text: note.trim(),
                color: defaultNotesColors.get(note.trim()) || Math.floor(Math.random() * 11),
            }));
    }
}
