import { beforeEach, describe, expect, test, waitUntil } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { GloryService } from "@pos_glory_cash/glory_service";
import { SocketIoService } from "@pos_glory_cash/utils/socket_io";

const sentMessages = [];

const mockSettings = {
    FunctionSetting: {
        OccupyEnable: "0",
        SessionEnable: "0",
        SessionMinute: "60",
        SoapDuplicateCheck: "0",
        SoapUserCheck: "0",
    },
};

const parsedMockSettings = {
    OccupyEnable: 0,
    SessionEnable: 0,
    SessionMinute: 60,
    SoapDuplicateCheck: 0,
    SoapUserCheck: 0,
};

const expectedDateTimeMessage =
    '<AdjustTimeRequest><Id>OdooPos</Id><SeqNo>00000000000</SeqNo><Date year="2019" month="3" day="11"/><Time hour="10" minute="30" second="0"/></AdjustTimeRequest>\0';
const expectedGetStatusMessage =
    '<StatusRequest><Id>OdooPos</Id><SeqNo>00000000000</SeqNo><RequireVerification type="1"/></StatusRequest>\0';
const expectedGetInventoryMessage =
    '<InventoryRequest><Id>OdooPos</Id><SeqNo>00000000000</SeqNo><Option type="2"/></InventoryRequest>\0';

beforeEach(() => {
    sentMessages.splice(0, sentMessages.length);
    patchWithCleanup(SocketIoService.prototype, {
        _responses: {},
        _xmlResponses: {},
        connect() {
            this.callbacks.onConnect();
        },
        _respondToMessageWith(message, response) {
            this._responses[message] = response;
        },
        _respondToXmlMessageWith(message, response) {
            this._xmlResponses[message] = response;
        },
        sendMessage(message) {
            sentMessages.push(message);
            if (message[0] in this._responses) {
                this.callbacks.onEvent(this._responses[message[0]]);
            } else if (message[0] === "xml send") {
                const xmlMessage = message[1].split("><")[0].slice(1);
                if (xmlMessage in this._xmlResponses) {
                    const strResponse = `<BbxEventRequest>${this._xmlResponses[xmlMessage]}</BbxEventRequest>`;
                    this.callbacks.onBinaryEvent(new Blob([strResponse]));
                }
            }
        },
    });
});

describe("on connecting", () => {
    test("checks credentials", async () => {
        const gloryService = new GloryService(() => {});
        gloryService.connect("mockIp");

        expect(sentMessages).toHaveLength(1);
        expect(sentMessages[0]).toEqual(["check credential", undefined]);
    });

    test("retrieves device settings", async () => {
        const gloryService = new GloryService(() => {});
        gloryService.socketIo._respondToMessageWith("check credential", ["credential ok"]);
        gloryService.socketIo._respondToMessageWith("getFunctionSetting", [
            "sendFunctionSetting",
            mockSettings,
        ]);
        gloryService.connect("mockIp");

        await waitUntil(() => sentMessages.length >= 2);

        expect(sentMessages[1]).toEqual(["getFunctionSetting"]);
        expect(gloryService.settings).toEqual(parsedMockSettings);
    });

    test("sets date and time", async () => {
        const gloryService = new GloryService(() => {});
        gloryService.socketIo._respondToMessageWith("check credential", ["credential ok"]);
        gloryService.socketIo._respondToMessageWith("getFunctionSetting", [
            "sendFunctionSetting",
            mockSettings,
        ]);
        gloryService.connect("mockIp");

        await waitUntil(() => sentMessages.length >= 3);

        expect(sentMessages[2]).toEqual(["xml send", expectedDateTimeMessage]);
    });

    test("retrieves device status", async () => {
        const gloryService = new GloryService(() => {});
        gloryService.socketIo._respondToMessageWith("check credential", ["credential ok"]);
        gloryService.socketIo._respondToMessageWith("getFunctionSetting", [
            "sendFunctionSetting",
            mockSettings,
        ]);
        gloryService.socketIo._respondToXmlMessageWith(
            "AdjustTimeRequest",
            '<AdjustTimeResponse result="0"/>'
        );
        gloryService.socketIo._respondToXmlMessageWith(
            "StatusRequest",
            '<StatusResponse result="0"><Code>0</Code></StatusResponse>'
        );
        gloryService.connect("mockIp");

        await waitUntil(() => sentMessages.length >= 4);

        expect(sentMessages[3]).toEqual(["xml send", expectedGetStatusMessage]);
        expect(gloryService.status).toBe("INITIALIZING");
    });

    test("retrieves initial inventory", async () => {
        const gloryService = new GloryService(() => {});
        gloryService.socketIo._respondToMessageWith("check credential", ["credential ok"]);
        gloryService.socketIo._respondToMessageWith("getFunctionSetting", [
            "sendFunctionSetting",
            mockSettings,
        ]);
        gloryService.socketIo._respondToXmlMessageWith(
            "AdjustTimeRequest",
            '<AdjustTimeResponse result="0"/>'
        );
        gloryService.socketIo._respondToXmlMessageWith(
            "StatusRequest",
            '<StatusResponse result="0"><Code>0</Code></StatusResponse>'
        );
        gloryService.socketIo._respondToXmlMessageWith(
            "InventoryRequest",
            '<InventoryResponse result="0"><Cash type="4"><Denomination fv="10"><Piece>5</Piece><Status>1</Status></Denomination></Cash></InventoryResponse>'
        );
        gloryService.connect("mockIp");

        await waitUntil(() => sentMessages.length >= 5);

        expect(sentMessages[4]).toEqual(["xml send", expectedGetInventoryMessage]);
        expect(gloryService.state.inventory).toHaveLength(1);
        expect(gloryService.state.inventory[0]).toEqual({
            value: 10,
            amount: 5,
            status: "NEAR_EMPTY",
        });
    });
});
