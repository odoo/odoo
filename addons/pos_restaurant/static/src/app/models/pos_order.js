import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PosOrder.prototype, {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        if (this.config.module_pos_restaurant) {
            this.customer_count = this.customer_count || 1;
        }
    },
    initState() {
        super.initState();
        this.uiState.selected_course_uuid = undefined;
    },
    getCustomerCount() {
        return this.customer_count;
    },
    setCustomerCount(count) {
        this.customer_count = Math.max(count, 0);
    },
    getTable() {
        return this.table_id;
    },
    get isBooked() {
        const res = super.isBooked;
        if (this.config.module_pos_restaurant) {
            return super.isBooked || !this.isDirectSale;
        }
        return res;
    },
    amountPerGuest(numCustomers = this.customer_count) {
        if (numCustomers === 0) {
            return 0;
        }
        return this.totalDue / numCustomers;
    },
    setBooked(booked) {
        this.uiState.booked = booked;
    },
    getName() {
        if (this.config.module_pos_restaurant) {
            if (this.isDirectSale) {
                return _t("Direct Sale");
            }
            if (this.getTable()) {
                const table = this.getTable();
                const child_tables = this.models["restaurant.table"].filter((t) => {
                    if (t.floor_id && t.floor_id.id === table.floor_id.id) {
                        return table.isParent(t);
                    }
                });
                let name = "T " + table.table_number.toString();
                for (const child_table of child_tables) {
                    name += ` & ${child_table.table_number}`;
                }
                return name;
            }
        }
        return super.getName(...arguments);
    },
    get isDirectSale() {
        return Boolean(
            this.config.module_pos_restaurant &&
                !this.table_id &&
                !this.floating_order_name &&
                this.state == "draft" &&
                !this.isRefund
        );
    },
    get isFilledDirectSale() {
        return this.isDirectSale && !this.isEmpty();
    },
    setPartner(partner) {
        if (this.config.module_pos_restaurant && this.isDirectSale) {
            this.floating_order_name = partner.name;
        }
        return super.setPartner(...arguments);
    },
    cleanCourses() {
        if (!this.hasCourses()) {
            return;
        }
        let lastFiredIndex = -1;
        const courses = this.courses;
        for (let i = courses.length - 1; i >= 0; i--) {
            if (courses[i].fired) {
                lastFiredIndex = i;
                break;
            }
        }
        const originalLength = courses.length;
        const removedCourses = [];
        const cleanedCourses = courses
            .filter((course, index) => {
                const shouldKeep = index <= lastFiredIndex || !course.isEmpty();
                if (!shouldKeep) {
                    removedCourses.push(course);
                }
                return shouldKeep;
            })
            .map((course, newIndex) => {
                course.index = newIndex + 1;
                return course;
            });
        removedCourses.forEach((course) => {
            course.delete();
        });
        if (cleanedCourses.length !== originalLength) {
            this.course_ids = cleanedCourses;
        }
    },
    get courses() {
        return this.course_ids.toSorted((a, b) => a.index - b.index);
    },
    hasCourses() {
        return this.course_ids.length > 0;
    },
    getFirstCourse() {
        return this.courses[0];
    },
    getLastCourse() {
        return this.courses.at(-1);
    },
    ensureCourseSelection() {
        if (!this.hasCourses()) {
            return;
        }
        // Select the first non fired course
        const nonFiredCourse = this.courses.find((course) => !course.fired);
        this.selectCourse(nonFiredCourse ?? this.getLastCourse());
    },
    deselectCourse() {
        this.selectCourse(undefined);
    },
    selectCourse(course) {
        if (course) {
            this.uiState.selected_course_uuid = course.uuid;
            this.deselectOrderline();
        } else {
            this.uiState.selected_course_uuid = undefined;
        }
    },
    getSelectedCourse() {
        if (!this.uiState.selected_course_uuid) {
            return;
        }
        return this.course_ids.find((course) => course.uuid === this.uiState.selected_course_uuid);
    },
    getNextCourseIndex() {
        return (
            this.course_ids.reduce(
                (maxIndex, course) => (course.index > maxIndex ? course.index : maxIndex),
                0
            ) + 1
        );
    },
});
