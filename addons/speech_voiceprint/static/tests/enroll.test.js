import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { VoiceprintEnroll } from "@speech_voiceprint/enroll/enroll";

const status = (overrides) => ({
    employee: "Aaron Ramírez",
    enrolled: false,
    active: false,
    enrolled_at: false,
    sample_seconds: 0,
    available: true,
    phrase: "Buenos días, lee esta frase en voz alta.",
    ...overrides,
});

test("the page shows the employee and the phrase before any recording", async () => {
    onRpc("/speech/voiceprint/status", () => status());
    await mountWithCleanup(VoiceprintEnroll, { props: { action: {} } });
    await animationFrame();

    expect(".o_speech_voiceprint strong").toHaveText("Aaron Ramírez");
    expect(".o_speech_voiceprint").toHaveText(/no voiceprint yet/);
    expect(".card-text").toHaveText(/lee esta frase/);
    expect("button.btn-link.text-danger").toHaveCount(0);
});

test("an enrolled voice offers deletion and shows a deactivated badge", async () => {
    onRpc("/speech/voiceprint/status", () =>
        status({
            enrolled: true,
            active: false,
            enrolled_at: "2026-09-01T10:00:00",
            sample_seconds: 24,
        }),
    );
    await mountWithCleanup(VoiceprintEnroll, { props: { action: {} } });
    await animationFrame();

    expect(".o_speech_voiceprint").toHaveText(/voice enrolled on 2026-09-01/);
    expect(".badge.text-bg-warning").toHaveText("deactivated by a leader");
    expect("button.btn-link.text-danger").toHaveCount(1);
});

test("a server without the model says so", async () => {
    onRpc("/speech/voiceprint/status", () => status({ available: false }));
    await mountWithCleanup(VoiceprintEnroll, { props: { action: {} } });
    await animationFrame();

    expect(".alert-warning").toHaveText(/not installed on this server/);
});
