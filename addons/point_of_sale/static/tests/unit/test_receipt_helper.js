import { patchWithCleanup, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { EpsonPrinter } from "@point_of_sale/app/utils/printer/epson_printer";
import { MainComponentsContainer } from "@web/core/main_components_container";

/**
 * Utility class to generate and validate printed POS receipts
 * (Order or Preparation).
 */
export class TestReceiptUtil {
    constructor(store, order, type = "order") {
        this.store = store;
        this.order = order || this.getOrderToPrint();
        this.type = type; // "order" | "preparation"
        this.tickets = [];
        if (!this.order) {
            throw new Error("TestReceipt: No order to print!");
        }
    }

    getOrderToPrint() {
        return this.getOrder();
    }

    async generateReceiptToTest() {
        const capturedTickets = [];
        patchWithCleanup(EpsonPrinter.prototype, {
            async printReceipt(receiptTmpl) {
                capturedTickets.push(receiptTmpl);
                return { successful: true };
            },
        });
        // Ensures RenderContainer is mounted so templates render correctly
        await mountWithCleanup(MainComponentsContainer);

        await this.triggerReceiptPrint();
        this.tickets = capturedTickets;
    }

    async triggerReceiptPrint() {
        if (this.type === "order") {
            return this.store.printReceipt({ order: this.order });
        }
        if (this.type === "preparation") {
            return this.store.sendOrderInPreparation(this.order);
        }
    }

    /**
     * Validate printed ticket content.
     *
     * @param {object[]} linesData  Expected line objects.
     * @param {object} opts
     *   - visibleInDom: strings that must appear in HTML
     *   - invisibleInDom: strings that must NOT appear in HTML
     *   - nbPrints: expected number of printed tickets
     * @param {number} ticketToCheck 1-based index of the ticket to validate
     */
    check(
        linesData = [],
        opts = { visibleInDom: [], invisibleInDom: [], nbPrints: 0 },
        ticketToCheck = 1
    ) {
        if (!this.tickets.length) {
            throw new Error("TestReceipt: No printed ticket available for checking.");
        }

        if (this.tickets.length < ticketToCheck) {
            throw new Error(
                `TestReceipt: Ticket index ${ticketToCheck} does not exist. Total: ${this.tickets.length}`
            );
        }

        const ticket = this.tickets[ticketToCheck - 1];
        const lines = ticket.querySelectorAll(".orderline");

        // Validate each printed line
        lines.forEach((line, index) => {
            this.checkLine(line, linesData[index]);
        });

        for (const text of opts.visibleInDom || []) {
            if (!ticket.innerHTML.includes(text)) {
                throw new Error(`Expected "${text}" to be visible in printed receipt.`);
            }
        }

        for (const text of opts.invisibleInDom || []) {
            if (ticket.innerHTML.includes(text)) {
                throw new Error(`"${text}" should NOT appear in printed receipt.`);
            }
        }
        return true;
    }

    checkLine(line, lineData) {
        if (!lineData) {
            return true;
        }
        if (this.type === "order") {
            return this.checkOrderLine(line, lineData);
        }
        if (this.type === "preparation") {
            return this.checkPreparationLine(line, lineData);
        }
    }

    /**
     * Validates a single Order receipt line.
     *
     * Expected `lineData` structure:
     *   {
     *       name: string,        // Expected product name
     *       qty: number,         // Expected quantity
     *       price?: number,      // Expected unit price
     *       infoList?: string[], // Expected additional info entries
     *   }
     */
    checkOrderLine(line, lineData) {
        const qty = line.querySelector(".product-name .qty")?.innerHTML;
        const name = line.querySelector(".product-name")?.children[1]?.textContent;
        const price = line.querySelector(".product-price")?.textContent || "";
        const infoList = line.querySelector(".info-list")?.textContent || "";

        if (lineData.qty != qty) {
            throw new Error(`Qty mismatch for ${name}: expected ${lineData.qty}, got ${qty}`);
        }

        if (lineData.name !== name) {
            throw new Error(`Name mismatch: expected "${lineData.name}", got "${name}".`);
        }

        if (lineData.price && !price.includes(lineData.price)) {
            throw new Error(`Price mismatch for ${name}: expected ${lineData.price}, got ${price}`);
        }

        if (lineData.infoList) {
            for (const info of lineData.infoList) {
                if (!infoList.includes(info)) {
                    throw new Error(`Missing info "${info}" for ${name}`);
                }
            }
        }
        return true;
    }

    /**
     * Validates a single Preparation receipt line.
     *
     * Expected `lineData` structure:
     *   {
     *       name: string,          // Expected product name
     *       qty: number,           // Expected quantity
     *       attributes?: string[], // Expected modifier/attribute values
     *   }
     */
    checkPreparationLine(line, lineData) {
        const qty = line.firstChild?.children[0]?.innerHTML;
        const name = line.firstChild?.children[1]?.innerHTML;

        if (lineData.qty != qty) {
            throw new Error(`Qty mismatch for ${name}: expected ${lineData.qty}, got ${qty}`);
        }

        if (lineData.name !== name) {
            throw new Error(
                `Name mismatch for ${name}: expected "${lineData.name}", got "${name}".`
            );
        }

        if (lineData.attributes) {
            const domAttrs = Object.values(line.children[1]?.children || []);
            const attrs = domAttrs.map((el) => el.innerHTML).filter(Boolean);
            for (const attr of lineData.attributes) {
                if (!attrs.some((a) => a.includes(attr))) {
                    throw new Error(`Missing attribute "${attr}" for ${name}`);
                }
            }
        }
        return true;
    }
}
