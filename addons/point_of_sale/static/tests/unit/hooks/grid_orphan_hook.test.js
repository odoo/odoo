import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { Component, signal, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { useGridOrphan } from "@point_of_sale/app/hooks/grid_orphan_hook";

class Grid extends Component {
    static template = xml`
        <div t-ref="this.gridRef" class="o_test_grid"
            t-attf-style="display: grid; width: 300px; grid-template-columns: repeat({{this.columns()}}, 1fr);">
            <div t-foreach="this.items()" t-as="item" t-key="item" t-out="item"/>
        </div>
    `;
    gridRef = signal.ref();
    columns = signal(3);
    items = signal([1, 2, 3, 4]);

    setup() {
        useGridOrphan(this.gridRef);
    }
}

test("useGridOrphan marks the last child alone on the last row", async () => {
    const grid = await mountWithCleanup(Grid);
    expect(".o_test_grid > :last-child").toHaveClass("o_pos_grid_orphan");
    expect(".o_pos_grid_orphan").toHaveCount(1);

    grid.items.set([1, 2, 3, 4, 5]);
    await animationFrame();
    expect(".o_pos_grid_orphan").toHaveCount(0);

    grid.items.set([1, 2, 3, 4, 5, 6, 7]);
    await animationFrame();
    expect(".o_test_grid > :last-child").toHaveClass("o_pos_grid_orphan");
    expect(".o_pos_grid_orphan").toHaveCount(1);

    grid.columns.set(1);
    await animationFrame();
    expect(".o_pos_grid_orphan").toHaveCount(0);
});
