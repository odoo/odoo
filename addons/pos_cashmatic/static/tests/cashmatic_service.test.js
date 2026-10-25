import { beforeEach, describe, expect, mockFetch, test } from "@odoo/hoot";
import { CashmaticService, POST_REQUESTS } from "@pos_cashmatic/cashmatic_service";

const mockFetches = [];
const receivedRequests = [];

const mockCashmaticRequest = (operation, message = "", data = {}, code = 0) => {
    mockFetches.push((url) => {
        const parsedUrl = new URL(url);
        if (parsedUrl.host !== "mock-ip:50301") {
            console.error("URL does not match expected");
            return;
        }
        const pathname = parsedUrl.pathname;
        if (pathname !== operation) {
            console.error(`Expected operation '${operation}', got '${pathname}'`);
            return;
        }

        return new Response(
            JSON.stringify({
                code,
                message: message,
                data: data,
            })
        );
    });
};

const mockActiveTransaction = (operation, inserted = 0, dispensed = 0) =>
    mockCashmaticRequest(POST_REQUESTS.activeTransaction, "No error", {
        operation,
        inserted,
        dispensed,
    });

const mockLastTransaction = (notDispensed = 0) =>
    mockCashmaticRequest(POST_REQUESTS.lastTransaction, "No error", { notDispensed });

beforeEach(() => {
    mockFetches.splice(0);
    receivedRequests.splice(0);
    mockFetch((url) => {
        const requestNum = receivedRequests.length;
        receivedRequests.push(url);

        if (mockFetches[requestNum]) {
            return mockFetches[requestNum](url);
        }

        console.error("Received fetch but no mock defined!");
    });
});

describe("connect", () => {
    test("sets credentials", () => {
        const cashmaticService = new CashmaticService();

        cashmaticService.connect("mock-ip", "mockUser", "mockPassword");

        expect(cashmaticService.ip).toBe("mock-ip");
        expect(cashmaticService.username).toBe("mockUser");
        expect(cashmaticService.password).toBe("mockPassword");
        expect(cashmaticService.state.amountInserted).toBe(0);
        expect(cashmaticService.state.amountDispensed).toBe(0);
    });
    test("renewOrLogin", async () => {
        const cashmaticService = new CashmaticService();
        cashmaticService.connect("mock-ip", "mockUser", "mockPassword");

        mockCashmaticRequest(POST_REQUESTS.renewToken, "No error");
        mockCashmaticRequest(POST_REQUESTS.login, "No error", {
            token: "cashmaticToken",
        });

        await cashmaticService.renewOrLogin();
        expect(cashmaticService.token).toBe("cashmaticToken");

        mockCashmaticRequest(POST_REQUESTS.renewToken, "No error", {
            token: "cashmaticRenewedToken",
        });

        await cashmaticService.renewOrLogin();
        expect(cashmaticService.token).toBe("cashmaticRenewedToken");
    });
});

describe("sendPaymentRequest", () => {
    test("works correctly for successful payment", async () => {
        const cashmaticService = new CashmaticService();
        cashmaticService.connect("mock-ip", "mockUser", "mockPassword");

        mockCashmaticRequest(POST_REQUESTS.renewToken, "No error", {
            token: "cashmaticRenewedToken",
        });

        mockCashmaticRequest(POST_REQUESTS.startPayment, "No error");
        mockActiveTransaction("payment");
        mockActiveTransaction("idle");
        mockLastTransaction(0);

        const notDispensed = await cashmaticService.sendPaymentRequest(510);

        expect(notDispensed).toBe(0);
    });

    test("returns notDispensed amount when cash cannot be fully dispensed", async () => {
        const cashmaticService = new CashmaticService();
        cashmaticService.connect("mock-ip", "mockUser", "mockPassword");

        mockCashmaticRequest(POST_REQUESTS.renewToken, "No error", {
            token: "cashmaticRenewedToken",
        });

        mockCashmaticRequest(POST_REQUESTS.startPayment, "No error");
        mockActiveTransaction("payment");
        mockActiveTransaction("idle");
        mockLastTransaction(100);
        const notDispensed = await cashmaticService.sendPaymentRequest(510);
        expect(notDispensed).toBe(100);
    });

    test("Cancel payment", async () => {
        const cashmaticService = new CashmaticService();
        cashmaticService.connect("mock-ip", "mockUser", "mockPassword");

        mockCashmaticRequest(POST_REQUESTS.renewToken, "No error", {
            token: "cashmaticRenewedToken",
        });
        mockCashmaticRequest(POST_REQUESTS.cancelPayment, "No error");
        mockActiveTransaction("idle");
        mockLastTransaction(0);

        const notDispensed = await cashmaticService.cancelCurrentPayment();

        expect(notDispensed).toBe(0);
        expect(receivedRequests.length).toBe(4);
    });

    test("Cancel payment with partial dispense", async () => {
        const cashmaticService = new CashmaticService();
        cashmaticService.connect("mock-ip", "mockUser", "mockPassword");

        mockCashmaticRequest(POST_REQUESTS.renewToken, "No error", {
            token: "cashmaticRenewedToken",
        });
        mockCashmaticRequest(POST_REQUESTS.cancelPayment, "No error");
        mockActiveTransaction("idle");
        mockLastTransaction(200);

        const notDispensed = await cashmaticService.cancelCurrentPayment();

        expect(notDispensed).toBe(200);
    });
});
