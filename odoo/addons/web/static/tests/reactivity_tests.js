/** @odoo-module **/

import { reactive, toRaw } from "@odoo/owl";

const {
    DateTime,
    Duration,
    FixedOffsetZone,
    IANAZone,
    Info,
    Interval,
    InvalidZone,
    Settings,
    SystemZone,
    Zone,
} = luxon;

QUnit.module("reactivity", () => {
    QUnit.test("Luxon objects can't be made reactive", async (assert) => {
        const obj = reactive({
            DateTime: DateTime.now(),
            Duration: Duration.fromObject({ seconds: 10 }),
            FixedOffsetZone: FixedOffsetZone.instance(0),
            IANAZone: IANAZone.create("CET"),
            Info: Info,
            Interval: Interval.before(DateTime.now(), { seconds: 10 }),
            InvalidZone: new InvalidZone("invalid"),
            Settings: new Settings(),
            SystemZone: new SystemZone(),
            Zone: new Zone(),
        });
        assert.strictEqual(obj.DateTime, toRaw(obj.DateTime));
        assert.strictEqual(obj.Duration, toRaw(obj.Duration));
        assert.strictEqual(obj.FixedOffsetZone, toRaw(obj.FixedOffsetZone));
        assert.strictEqual(obj.IANAZone, toRaw(obj.IANAZone));
        assert.strictEqual(obj.Info, toRaw(obj.Info));
        assert.strictEqual(obj.Interval, toRaw(obj.Interval));
        assert.strictEqual(obj.InvalidZone, toRaw(obj.InvalidZone));
        assert.strictEqual(obj.Settings, toRaw(obj.Settings));
        assert.strictEqual(obj.SystemZone, toRaw(obj.SystemZone));
        assert.strictEqual(obj.Zone, toRaw(obj.Zone));
    });
});
