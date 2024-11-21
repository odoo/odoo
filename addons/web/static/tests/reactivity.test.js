import { describe, expect, test } from "@odoo/hoot";
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

describe.current.tags("headless");

test(`Luxon objects can't be made reactive`, async () => {
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
    expect(obj.DateTime).toBe(toRaw(obj.DateTime));
    expect(obj.Duration).toBe(toRaw(obj.Duration));
    expect(obj.FixedOffsetZone).toBe(toRaw(obj.FixedOffsetZone));
    expect(obj.IANAZone).toBe(toRaw(obj.IANAZone));
    expect(obj.Info).toBe(toRaw(obj.Info));
    expect(obj.Interval).toBe(toRaw(obj.Interval));
    expect(obj.InvalidZone).toBe(toRaw(obj.InvalidZone));
    expect(obj.Settings).toBe(toRaw(obj.Settings));
    expect(obj.SystemZone).toBe(toRaw(obj.SystemZone));
    expect(obj.Zone).toBe(toRaw(obj.Zone));
});
