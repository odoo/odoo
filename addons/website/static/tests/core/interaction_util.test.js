import { expect, test } from "@odoo/hoot";
import { Interaction } from "@web/public/interaction";
import { buildEditableInteractions } from "@website/core/website_edit_service";

test("buildEditableInteractions concrete", async () => {
    const doStuff = () => {};

    class Base extends Interaction {
        stuff() {
            doStuff();
        }
    }
    const BaseEdit = (I) =>
        class extends I {
            stuff() {} // don't
        };
    class Specific extends Base {
        otherStuff() {
            doStuff("other");
        }
    }
    const builders = [{ Interaction: Base, mixin: BaseEdit }, { Interaction: Specific }];
    const [baseEI, specificEI] = buildEditableInteractions(builders);
    expect(baseEI.name).toBe("Base__mixin");
    expect(specificEI.name).toBe("Specific__mixin");
    expect(baseEI.__proto__.__proto__).toBe(Base);
    expect(baseEI.prototype.stuff.toString()).not.toBe(Base.prototype.stuff.toString());
    expect(specificEI.__proto__.__proto__).toBe(Specific);
    expect(specificEI.prototype.stuff.toString()).not.toBe(Specific.prototype.stuff.toString());
    expect(baseEI.prototype.stuff.toString()).toEqual(specificEI.prototype.stuff.toString());
});

test("buildEditableInteractions abstract", async () => {
    const doStuff = () => {};

    class AbstractBase extends Interaction {
        stuff() {
            doStuff();
        }
    }
    const AbstractBaseEdit = (I) =>
        class extends I {
            stuff() {} // don't
        };
    class AbstractIntermediate extends AbstractBase {
        moreStuff() {
            doStuff("more");
        }
    }
    class Specific extends AbstractIntermediate {
        otherStuff() {
            doStuff("other");
        }
    }
    const builders = [
        { Interaction: AbstractBase, mixin: AbstractBaseEdit, isAbstract: true },
        { Interaction: AbstractIntermediate, isAbstract: true },
        { Interaction: Specific },
    ];
    const EIs = buildEditableInteractions(builders);
    expect(EIs.length).toBe(1);
    const EI = EIs[0];
    expect(EI.name).toBe("Specific__mixin");
    expect(EI.__proto__.__proto__).toBe(Specific);
    expect(EI.prototype.stuff.toString()).not.toBe(Specific.prototype.stuff.toString());
});
