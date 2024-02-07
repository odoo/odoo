/** @odoo-module */

import { Component, useEffect, useRef } from "@odoo/owl";
import { CenteredIcon } from "@point_of_sale/app/generic_components/centered_icon/centered_icon";

export class OrderWidget extends Component {
    static template = "point_of_sale.OrderWidget";
    static props = {
        lines: { type: Array, element: Object },
        slots: { type: Object },
        total: { type: String, optional: true },
        tax: { type: String, optional: true },
        groupBy: {
            type: [Object, { value: null }],
            optional: true,
        },
    };
    static components = { CenteredIcon };
    setup() {
        this.scrollableRef = useRef("scrollable");
        useEffect(() => {
            this.scrollableRef.el
                ?.querySelector(".orderline.selected")
                ?.scrollIntoView({ behavior: "smooth", block: "start" });
        });
    }

    getGroupedLines() {
        const check = this.props.groupBy.check;
        const filteredLines = this.props.lines.reduce((acc, line) => {
            for (const d of this.props.groupBy.data) {
                const result = check(d.id, line);

                if (result === true) {
                    if (!acc[d.id]) {
                        acc[d.id] = {
                            id: d.id,
                            sequence: d.sequence,
                            lines: [],
                            group: d.name,
                            onClick: () => this.props.groupBy.onClick(d),
                        };
                    }

                    acc[d.id].lines.push(line);
                } else if (result === false) {
                    if (!acc["no_group"]) {
                        acc["no_group"] = {
                            id: "no_group",
                            sequence: 9999,
                            lines: [],
                            group: "Others",
                            onClick: () => this.props.groupBy.onClick(null),
                        };
                    }

                    acc["no_group"].lines.push(line);
                    return acc;
                }
            }

            return acc;
        }, {});

        const data = Object.values(filteredLines);
        data.sort((a, b) => a.sequence - b.sequence);

        for (const d of data) {
            d.lines = d.lines.sort((a, b) => a.id - b.id);
        }

        return data;
    }
}
