import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";

patch(Orderline.prototype, {
    get lineContainerClasses() {
        const classes = super.lineContainerClasses;

        const hasDifferentCourse =
            this.line.combo_parent_id &&
            this.line.course_id &&
            this.line.course_id?.id !== this.line.combo_parent_id.course_id?.id;

        if (hasDifferentCourse) {
            classes["border-start"] = false;
            classes["orderline-combo fst-italic ms-4"] = false;
        }

        return classes;
    },

    get lineScreenValues() {
        const vals = super.lineScreenValues;

        const hasDifferentCourse =
            this.line.combo_parent_id &&
            this.line.course_id &&
            this.line.course_id?.id !== this.line.combo_parent_id.course_id?.id;

        vals.isIncluded = Boolean(hasDifferentCourse);
        vals.comboParentName = this.line.orderDisplayProductName?.comboParentName;

        return vals;
    },
});
