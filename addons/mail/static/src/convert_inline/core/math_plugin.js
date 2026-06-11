import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";

export class MathPlugin extends Plugin {
    static id = "math";
    static shared = [
        "areRectEqual",
        "pixelTolerance",
        "isNegativeZero",
        "isPositiveZero",
        "isZero",
        "overlapX",
        "overlapY",
        "gapX",
        "gapY",
        "siblingSpacing",
        "containerPadding",
    ];

    pixelTolerance() {
        // TODO EGGMAIL: evaluate if 0.25 - 1 is a reasonable range for tolerance
        return Math.min(
            1,
            Math.max(0.25, 1 / this.config.referenceDocument.defaultView.devicePixelRatio)
        );
    }

    areRectEqual(rect1, rect2) {
        return (
            this.isZero(rect1.width - rect2.width) &&
            this.isZero(rect1.height - rect2.height) &&
            this.isZero(rect1.width - this.overlapX(rect1, rect2)) &&
            this.isZero(rect1.height - this.overlapY(rect1, rect2))
        );
    }

    isNegativeZero(value) {
        return value === 0 || (value < 0 && value > -this.pixelTolerance());
    }

    isPositiveZero(value) {
        return value === 0 || (value > 0 && value < this.pixelTolerance());
    }

    isZero(value) {
        return this.isPositiveZero(value) || this.isNegativeZero(value);
    }

    dx({ left: l1, right: r1 }, { left: l2, right: r2 }) {
        return Math.max(l1, l2) - Math.min(r1, r2);
    }

    dy({ top: t1, bottom: b1 }, { top: t2, bottom: b2 }) {
        return Math.max(t1, t2) - Math.min(b1, b2);
    }

    overlapX(rect1, rect2) {
        const dx = this.dx(rect1, rect2);
        return this.isZero(dx) ? 0 : Math.max(0, -dx);
    }

    overlapY(rect1, rect2) {
        const dy = this.dy(rect1, rect2);
        return this.isZero(dy) ? 0 : Math.max(0, -dy);
    }

    gapX(rect1, rect2) {
        const dx = this.dx(rect1, rect2);
        return this.isZero(dx) ? 0 : Math.max(0, dx);
    }

    gapY(rect1, rect2) {
        const dy = this.dy(rect1, rect2);
        return this.isZero(dy) ? 0 : Math.max(0, dy);
    }

    siblingSpacing(siblingRect1, siblingRect2) {
        return {
            // TODO EGGMAIL: reconsider the 4x4 quadrant with 2 empty space cells,
            // sometimes it may be better to approximate to a row/column if the
            // spaces are not meaningful. And the reverse is also true, sometimes
            // it may be useful to handle a double overlap as rows/columns.
            row: !this.overlapX(siblingRect1, siblingRect2),
            column: !this.overlapY(siblingRect1, siblingRect2),
            gapX: this.gapX(siblingRect1, siblingRect2),
            gapY: this.gapY(siblingRect1, siblingRect2),
        };
    }

    containerPadding(outerRect, innerRect) {
        const { left: li, right: ri, top: ti, bottom: bi } = innerRect;
        const { left: lo, right: ro, top: to, bottom: bo } = outerRect;
        // TODO EGGMAIL: reconsider: do not allow inner elements to overflow outside
        // of their parent (such overflow will be ignored)
        const top = ti - to;
        const left = li - lo;
        const bottom = bo - bi;
        const right = ro - ri;
        return {
            top: this.isZero(top) ? 0 : Math.max(0, top),
            left: this.isZero(left) ? 0 : Math.max(0, left),
            bottom: this.isZero(bottom) ? 0 : Math.max(0, bottom),
            right: this.isZero(right) ? 0 : Math.max(0, right),
        };
    }
}

registry.category("mail-html-conversion-core-plugins").add(MathPlugin.id, MathPlugin);
