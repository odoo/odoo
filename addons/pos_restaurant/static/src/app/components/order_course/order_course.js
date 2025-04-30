import { Component } from "@odoo/owl";

export class OrderCourse extends Component {
    static template = "pos_restaurant.OrderCourse";
    static props = {
        course: Object,
        course_index: Number,
        slots: { type: Object, optional: true },
    };

    get course() {
        return this.props.course;
    }

    clickCourse(evt, course) {
        const order = course.order_id;
        order.selectCourse(course);
    }
}
