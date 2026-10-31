import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";

patch(Orderline.prototype, {
    get lineContainerClasses() {
        const classes = super.lineContainerClasses;

        if (this.isOutsideParentCourse) {
            classes["border-start"] = false;
            classes["orderline-combo fst-italic ms-4"] = false;
        }

        return classes;
    },

    get lineScreenValues() {
        const vals = super.lineScreenValues;

        if (!this.line.product_id) {
            return vals;
        }

        vals.isOutsideParentCourse = this.isOutsideParentCourse;

        return vals;
    },

    get isOutsideParentCourse() {
        return Boolean(
            (this.line.course_id &&
                this.line.combo_parent_id &&
                this.line.course_id?.id !== this.line.combo_parent_id.course_id?.id) ||
                (!this.line.course_id && this.env.services.pos.config.use_course_allocation)
        );
    },
});
