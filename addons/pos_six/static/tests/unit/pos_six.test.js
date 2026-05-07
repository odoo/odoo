import { expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-dom";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { createPaymentLine, getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

definePosModels();

// Stand-in for the WASM-loaded `timapi` global. Captures every constructor and
// every fire-and-forget call so tests can assert what `PaymentSix` asked the
// terminal to do.
function fakeTimapi() {
    const calls = {
        terminals: [],
        transactionAsync: [],
        balanceAsync: [],
        cancel: [],
        printOptions: [],
    };

    class TerminalSettings {}
    class TransactionData {}
    class Amount {
        constructor(value, currency, decimals) {
            this.value = value;
            this.currency = currency;
            this.decimals = decimals;
        }
    }
    class PrintOption {
        constructor(recipient, format, width, flags) {
            Object.assign(this, { recipient, format, width, flags });
        }
    }
    class DefaultTerminalListener {
        transactionCompleted() {}
        balanceCompleted() {}
    }
    class Terminal {
        constructor(settings) {
            this.settings = settings;
            this.listeners = [];
            this.printOptions = [];
            this.transactionData = null;
            calls.terminals.push(this);
        }
        setPosId(id) {
            this.posId = id;
        }
        setUserId(id) {
            this.userId = id;
        }
        addListener(listener) {
            this.listeners.push(listener);
        }
        setPrintOptions(options) {
            this.printOptions = options;
            calls.printOptions.push({ terminal: this, options });
        }
        transactionAsync(type, amount) {
            calls.transactionAsync.push({ terminal: this, type, amount });
        }
        balanceAsync() {
            calls.balanceAsync.push({ terminal: this });
        }
        cancel() {
            calls.cancel.push({ terminal: this });
        }
        setTransactionData(data) {
            this.transactionData = data;
        }
    }

    const constants = {
        ConnectionMode: { onFixIp: "onFixIp" },
        Recipient: { merchant: "merchant", cardholder: "cardholder" },
        PrintFormat: { normal: "normal" },
        PrintFlag: { suppressHeader: "sH", suppressEcrInfo: "sE" },
        TransactionType: { purchase: "purchase", credit: "credit", reversal: "reversal" },
        ResultCode: {
            ok: "ok",
            apiCancelEcr: "apiCancelEcr",
            declinedWrongPin: "declinedWrongPin",
        },
        Currency: { USD: "USD", EUR: "EUR" },
    };

    return {
        timapi: {
            Terminal,
            TerminalSettings,
            Amount,
            TransactionData,
            PrintOption,
            DefaultTerminalListener,
            log: () => {},
            LogRecord: { LogLevel: { warning: "warning" } },
            constants,
        },
        calls,
    };
}

function installFakeTimapi() {
    const fake = fakeTimapi();
    patchWithCleanup(window, { timapi: fake.timapi });
    return fake;
}

function getSixPm(store, ip) {
    return store.models["pos.payment.method"].find(
        (pm) => pm.payment_provider === "six" && pm.six_terminal_ip === ip
    );
}

test("six_terminal_ip with explicit port is parsed and ports are numeric", async () => {
    installFakeTimapi();
    const store = await setupPosEnv();

    const sixPm = getSixPm(store, "10.0.0.1:8080");
    const { settings } = sixPm.payment_interface.terminal;

    expect(settings.connectionIPString).toBe("10.0.0.1");
    expect(settings.connectionIPPort).toBe(8080);
    expect(typeof settings.connectionIPPort).toBe("number");
});

test("six_terminal_ip without port falls back to 80", async () => {
    installFakeTimapi();
    const store = await setupPosEnv();

    const sixPm = getSixPm(store, "10.0.0.2");
    const { settings } = sixPm.payment_interface.terminal;

    expect(settings.connectionIPString).toBe("10.0.0.2");
    expect(settings.connectionIPPort).toBe(80);
});

test("payment methods with the same six_terminal_ip share one Terminal instance", async () => {
    const { calls } = installFakeTimapi();
    const store = await setupPosEnv();

    const a = store.models["pos.payment.method"].get(100);
    const c = store.models["pos.payment.method"].get(102);

    expect(a.payment_interface.terminal).toBe(c.payment_interface.terminal);
    // Two distinct IPs (10.0.0.1:8080 shared across A & C, 10.0.0.2 for B) → 2 terminals.
    expect(calls.terminals.length).toBe(2);
});

test("sendPaymentRequest with positive amount sends a 'purchase'", async () => {
    const { timapi, calls } = installFakeTimapi();
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const sixPm = getSixPm(store, "10.0.0.1:8080");

    const line = createPaymentLine(store, order, sixPm, { amount: 25 });

    sixPm.payment_interface.sendPaymentRequest(line);
    await tick();

    const last = calls.transactionAsync.at(-1);
    expect(last.type).toBe(timapi.constants.TransactionType.purchase);
    expect(last.amount.value).toBeGreaterThan(0);
    expect(line.payment_status).toBe("waitingCard");
});

test("sendPaymentRequest with negative amount sends a 'credit' (refund), not 'reversal'", async () => {
    // Regression: using TransactionType.reversal for negative amounts means the
    // SDK voids the last transSeq with no card/PIN interaction, so terminal-side
    // errors (declined, wrong PIN) never reach the POS.
    const { timapi, calls } = installFakeTimapi();
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const sixPm = getSixPm(store, "10.0.0.1:8080");

    const line = createPaymentLine(store, order, sixPm, { amount: -10 });

    sixPm.payment_interface.sendPaymentRequest(line);
    await tick();

    const last = calls.transactionAsync.at(-1);
    expect(last.type).toBe(timapi.constants.TransactionType.credit);
    expect(last.type).not.toBe(timapi.constants.TransactionType.reversal);
    // Amount must always be positive; only the TransactionType conveys direction.
    expect(last.amount.value).toBeGreaterThan(0);
});

test("transaction completing with an exception puts the line in 'retry'", async () => {
    const { timapi } = installFakeTimapi();
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const sixPm = getSixPm(store, "10.0.0.1:8080");

    const line = createPaymentLine(store, order, sixPm, { amount: 25 });

    const paymentPromise = line.pay();
    await tick();
    sixPm.payment_interface._onTransactionComplete(
        {
            exception: {
                resultCode: timapi.constants.ResultCode.declinedWrongPin,
                errorText: "Wrong PIN",
            },
        },
        null
    );
    const success = await paymentPromise;

    expect(!!success).toBe(false);
    expect(line.payment_status).toBe("retry");
});

test("transaction completing successfully puts the line in 'done' and stores transSeq", async () => {
    installFakeTimapi();
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const sixPm = getSixPm(store, "10.0.0.1:8080");

    const line = createPaymentLine(store, order, sixPm, { amount: 25 });

    const paymentPromise = line.pay();
    await tick();
    sixPm.payment_interface._onTransactionComplete(
        {},
        {
            transactionInformation: { transSeq: 12345 },
            printData: { receipts: {} },
        }
    );
    const success = await paymentPromise;

    expect(success).toBe(true);
    expect(line.payment_status).toBe("done");
    expect(sixPm.payment_interface.terminal.transactionData.transSeq).toBe(12345);
});

test("Navbar.sendBalance fans out to every configured SIX terminal", async () => {
    const { calls } = installFakeTimapi();
    const store = await setupPosEnv();

    const navbar = Object.create(Navbar.prototype);
    navbar.pos = store;
    navbar.sendBalance();

    // 3 SIX payment methods configured → sendBalance called 3 times. PMs 100 and
    // 102 share a Terminal, so 2 of the 3 calls hit the same `balanceAsync`.
    expect(calls.balanceAsync.length).toBe(3);
});
