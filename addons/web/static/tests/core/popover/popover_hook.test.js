import { animationFrame, expect, getFixture, test } from "@odoo/hoot";
import { Component, onMounted, props, signal, types as t, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { usePopover } from "@web/core/popover/popover_hook";

test("close popover when component is unmounted", async () => {
    class Comp extends Component {
        static template = xml`<div t-att-id="this.props.id">in popover</div>`;
    }

    class CompWithPopover extends Component {
        static template = xml`<div />`;

        props = props({ id: t.string() });

        setup() {
            const popover = usePopover(Comp);
            onMounted(() => {
                popover.open(getFixture(), { id: this.props.id });
            });
        }
    }

    class Parent extends Component {
        static components = { CompWithPopover };
        static template = xml`
            <CompWithPopover id="'comp1'" t-if="this.showFirst()" />
            <CompWithPopover id="'comp2'" t-if="this.showSecond()" />
        `;

        showFirst = showFirst;
        showSecond = showSecond;
    }

    const showFirst = signal(true);
    const showSecond = signal(true);

    await mountWithCleanup(Parent);

    expect(".o_popover").toHaveCount(2);
    expect(".o_popover #comp1").toHaveCount(1);
    expect(".o_popover #comp2").toHaveCount(1);

    showFirst.set(false);
    await animationFrame();
    await animationFrame();

    expect(".o_popover").toHaveCount(1);
    expect(".o_popover #comp1").toHaveCount(0);
    expect(".o_popover #comp2").toHaveCount(1);

    showSecond.set(false);
    await animationFrame();
    await animationFrame();

    expect(".o_popover").toHaveCount(0);
    expect(".o_popover #comp1").toHaveCount(0);
    expect(".o_popover #comp2").toHaveCount(0);
});

test("popover opened from another", async () => {
    class Comp extends Component {
        static id = 0;
        static template = xml`
            <div class="p-4">
                <button class="pop-open" t-on-click="(ev) => this.popover.open(ev.target, {})">open popover</button>
            </div>
        `;
        static props = ["*"];
        setup() {
            this.popover = usePopover(Comp, {
                popoverClass: `popover-${++Comp.id}`,
            });
        }
    }

    await mountWithCleanup(Comp);

    await contains(".pop-open").click();
    expect(".popover-1").toHaveCount(1);

    await contains(".popover-1 .pop-open").click();
    expect(".o_popover").toHaveCount(2);
    expect(".popover-1").toHaveCount(1);
    expect(".popover-2").toHaveCount(1);

    await contains(".popover-2 .pop-open").click();
    expect(".o_popover").toHaveCount(3);
    expect(".popover-1").toHaveCount(1);
    expect(".popover-2").toHaveCount(1);
    expect(".popover-3").toHaveCount(1);

    await contains(".popover-3").click();
    expect(".o_popover").toHaveCount(3);
    expect(".popover-1").toHaveCount(1);
    expect(".popover-2").toHaveCount(1);
    expect(".popover-3").toHaveCount(1);

    await contains(".popover-2").click();
    expect(".o_popover").toHaveCount(2);
    expect(".popover-1").toHaveCount(1);
    expect(".popover-2").toHaveCount(1);

    await contains(document.body).click();
    expect(".o_popover").toHaveCount(0);
});
