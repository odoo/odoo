import { expect } from "@odoo/hoot";
import { renderToElement } from "@web/core/utils/render";

export const normalizeText = (value = "") => value.replace(/\s+/g, " ").trim();

export const normalizeAmount = (value) =>
    value === false || value === undefined || value === null
        ? value
        : String(value)
              .replace(/[^\d,.-]/g, "")
              .replace(/,/g, "");

export const renameProduct = (productTemplate, name) => {
    productTemplate.name = name;
    productTemplate.display_name = name;
    productTemplate.product_variant_ids[0].name = name;
    productTemplate.product_variant_ids[0].display_name = name;
};

export const setProductPrice = (productTemplate, price, taxes = productTemplate.taxes_id) => {
    productTemplate.list_price = price;
    productTemplate.taxes_id = taxes;
    productTemplate.product_variant_ids[0].lst_price = price;
};

export const addPayment = (order, paymentMethod, amount = undefined) => {
    order.addPaymentline(paymentMethod);
    const paymentLine = order.payment_ids.at(-1);
    if (amount !== undefined) {
        paymentLine.setAmount(amount);
    }
    return paymentLine;
};

export const renderReceipt = (store, order, basic = false) => {
    const data = store.ticketPrinter.getOrderReceiptData(order, { basic });
    return {
        data,
        ticket: renderToElement("point_of_sale.pos_order_receipt", data),
    };
};

export const renderOrderChangeReceipt = (store, order, opts = {}, filterCategoryIds = null) => {
    const generator = store.ticketPrinter.getGenerator({ models: store.models, order });
    const categoryIds = filterCategoryIds
        ? new Set(filterCategoryIds)
        : new Set(store.models["pos.category"].getAll().map((c) => c.id));
    const changes = generator.generatePreparationData(categoryIds, opts);
    const tickets = changes.map((data) =>
        renderToElement("point_of_sale.pos_order_change_receipt", data)
    );
    return { changes, tickets };
};

export const renderSaleDetailsReceipt = (store, saleDetails) => {
    const generator = store.ticketPrinter.getGenerator({ models: store.models });
    const data = generator.generateSaleDetailsData(saleDetails);
    const ticket = renderToElement("point_of_sale.pos_sale_details_receipt", data);
    return { data, ticket };
};

export const renderTipReceipt = (store, order, name = "") => {
    const generator = store.ticketPrinter.getGenerator({ models: store.models, order });
    const data = generator.generateTipData(name);
    const ticket = renderToElement("point_of_sale.pos_tip_receipt", data);
    return { data, ticket };
};

export const renderCashMoveReceipt = (store, { reason, translatedType, formattedAmount }) => {
    const generator = store.ticketPrinter.getGenerator({ models: store.models });
    const data = generator.generateCashMoveData({ reason, translatedType, formattedAmount });
    const ticket = renderToElement("point_of_sale.pos_cash_move_receipt", data);
    return { data, ticket };
};

export const assertCssRule = (root, rule) => {
    const matches = [...root.querySelectorAll(rule.css)];
    if (!matches.length) {
        if (rule.negation) {
            return;
        }
        throw new Error(`CSS rule ${rule.css} not found in receipt.`);
    }
    if (rule.length !== undefined) {
        expect(matches).toHaveLength(rule.length);
    }
    if (rule.text) {
        const found = matches.some((match) => normalizeText(match.textContent).includes(rule.text));
        expect(found).toBe(!rule.negation, {
            message: `CSS rule ${rule.css} text content should ${
                rule.negation ? "not" : ""
            } include "${rule.text}"`,
        });
    }
};

export const expectReceiptPayload = (data, expected) => {
    if (expected.total_amount !== undefined) {
        expect(normalizeAmount(data.extra_data.prices.total_amount)).toBe(
            normalizeAmount(expected.total_amount)
        );
    }

    if ("rounding_amount" in expected) {
        expect(normalizeAmount(data.extra_data.prices.rounding_amount || false)).toBe(
            normalizeAmount(expected.rounding_amount || false)
        );
    }

    if (expected.payment_lines) {
        expect(data.payments).toHaveLength(expected.payment_lines.length);
        expected.payment_lines.forEach((line, index) => {
            expect(data.payments[index].payment_method_data.name).toBe(line.name);
            if (line.amount !== undefined) {
                expect(normalizeAmount(data.payments[index].amount)).toBe(
                    normalizeAmount(line.amount)
                );
            }
        });
    }

    if (expected.orderlines) {
        expect(data.lines).toHaveLength(expected.orderlines.length);
        expected.orderlines.forEach((line, index) => {
            expect(data.lines[index].product_data.display_name).toInclude(line.name);
            if (line.quantity !== undefined) {
                expect(String(data.lines[index].qty)).toBe(line.quantity);
            }
            if (line.price_unit !== undefined) {
                expect(normalizeAmount(data.lines[index].unit_price)).toBe(
                    normalizeAmount(line.price_unit)
                );
            }
            if (line.line_price !== undefined) {
                expect(normalizeAmount(data.lines[index].price_subtotal_incl)).toBe(
                    normalizeAmount(line.line_price)
                );
            }
        });
    }
};

export const expectTicketData = (ticket, data, basic = false) => {
    if (data.total_amount) {
        const total = ticket.querySelector(".total-amount");
        expect(Boolean(total)).toBe(true);
        expect(normalizeText(total.textContent)).toInclude(data.total_amount);
    }

    if (data.logo) {
        const logo = ticket.querySelector("div[name='logo'] img");
        expect(Boolean(logo)).toBe(true);
        expect(logo.src).toInclude(data.logo);
    } else if (data.logo === false) {
        expect(Boolean(ticket.querySelector("div[name='logo'] img"))).toBe(false);
    }

    if (data.contact_info) {
        expect(normalizeText(ticket.textContent)).toInclude(data.contact_info);
    }

    if (data.is_rounding || data.rounding_amount) {
        const rounding = ticket.querySelector(".rounding-amount");
        expect(Boolean(rounding)).toBe(true);
        if (data.rounding_amount) {
            expect(normalizeText(rounding.textContent)).toInclude(data.rounding_amount);
        }
    } else if (data.is_rounding === false) {
        expect(Boolean(ticket.querySelector(".rounding-amount"))).toBe(false);
    }

    if (data.is_change || data.change_amount) {
        const change = ticket.querySelector(".change-amount");
        expect(Boolean(change)).toBe(true);
        if (data.change_amount) {
            expect(normalizeText(change.textContent)).toInclude(data.change_amount);
        }
    } else if (data.is_change === false) {
        expect(Boolean(ticket.querySelector(".change-amount"))).toBe(false);
    }

    if (data.is_qr_code) {
        expect(Boolean(ticket.querySelector(".invoice-qr-code"))).toBe(true);
    } else if (data.is_qr_code === false) {
        expect(Boolean(ticket.querySelector(".invoice-qr-code"))).toBe(false);
    }

    if (data.payment_lines) {
        const paymentLines = [...ticket.querySelectorAll(".payment-line")];
        expect(paymentLines).toHaveLength(data.payment_lines.length);
        data.payment_lines.forEach((line, index) => {
            const paymentLine = paymentLines[index];
            expect(normalizeText(paymentLine.firstElementChild.textContent)).toBe(line.name);
            if (line.amount) {
                expect(normalizeText(paymentLine.lastElementChild.textContent)).toInclude(
                    line.amount
                );
            }
        });
    }

    if (data.orderlines) {
        const lines = [...ticket.querySelectorAll(".lines")];
        expect(lines).toHaveLength(data.orderlines.length);
        data.orderlines.forEach((line, index) => {
            const orderline = lines[index];
            expect(normalizeText(orderline.querySelector(".name").textContent)).toInclude(
                line.name
            );
            if (line.quantity) {
                expect(normalizeText(orderline.querySelector(".qty").textContent)).toBe(
                    line.quantity
                );
            }
            if (basic) {
                expect(Boolean(orderline.querySelector(".price-unit"))).toBe(false);
                expect(Boolean(orderline.querySelector(".price-incl"))).toBe(false);
            } else {
                if (line.price_unit) {
                    const unitPrices = [...orderline.querySelectorAll(".price-unit")];
                    expect(
                        unitPrices.some((price) => price.textContent.includes(line.price_unit))
                    ).toBe(true);
                }
                if (line.line_price) {
                    expect(
                        normalizeText(orderline.querySelector(".price-incl").textContent)
                    ).toInclude(line.line_price);
                }
            }
            for (const rule of line.cssRules || []) {
                assertCssRule(orderline, rule);
            }
        });
    }

    for (const rule of data.cssRules || []) {
        assertCssRule(ticket, rule);
    }

    if (data.invisibleInDom) {
        const ticketHtml = ticket.innerHTML;
        for (const notInDom of data.invisibleInDom) {
            expect(ticketHtml.includes(notInDom)).toBe(false, {
                message: `"${notInDom}" should not appear in the ticket`,
            });
        }
    }

    if (data.visibleInDom) {
        const ticketHtml = ticket.innerHTML;
        for (const inDom of data.visibleInDom) {
            expect(ticketHtml.includes(inDom)).toBe(true, {
                message: `"${inDom}" should appear in the ticket`,
            });
        }
    }
};

export const expectOrderChangeTicket = (ticket, expected) => {
    if (expected.title) {
        const titleEl = ticket.querySelector("div[name='body'] .text-insane");
        expect(Boolean(titleEl)).toBe(true);
        expect(normalizeText(titleEl.textContent)).toInclude(expected.title);
    }

    if (expected.is_reprint) {
        expect(normalizeText(ticket.querySelector("div[name='body']").textContent)).toInclude(
            "DUPLICATE"
        );
    } else if (expected.is_reprint === false) {
        expect(
            normalizeText(ticket.querySelector("div[name='body']").textContent).includes(
                "DUPLICATE"
            )
        ).toBe(false);
    }

    if (expected.config_name) {
        const header = ticket.querySelector("div[name='employee-info']");
        expect(Boolean(header)).toBe(true);
        expect(normalizeText(header.textContent)).toInclude(expected.config_name);
    }

    if (expected.orderlines) {
        const lines = [...ticket.querySelectorAll(".orderline")];
        expect(lines).toHaveLength(expected.orderlines.length);
        expected.orderlines.forEach((line, index) => {
            const orderline = lines[index];
            if (line.name) {
                const productName = orderline.querySelector(".product-name");
                expect(normalizeText(productName.textContent)).toInclude(line.name);
            }
            if (line.quantity) {
                expect(normalizeText(orderline.textContent)).toInclude(line.quantity);
            }
            if (line.customer_note) {
                const note = orderline.querySelector(".text-italic");
                expect(Boolean(note)).toBe(true);
                expect(normalizeText(note.textContent)).toInclude(line.customer_note);
            }
        });
    }

    if (expected.invisibleInDom) {
        const ticketHtml = ticket.innerHTML;
        for (const notInDom of expected.invisibleInDom) {
            expect(ticketHtml.includes(notInDom)).toBe(false, {
                message: `"${notInDom}" should not appear in the preparation ticket`,
            });
        }
    }

    if (expected.visibleInDom) {
        const ticketHtml = ticket.innerHTML;
        for (const inDom of expected.visibleInDom) {
            expect(ticketHtml.includes(inDom)).toBe(true, {
                message: `"${inDom}" should appear in the preparation ticket`,
            });
        }
    }
};

export const expectSaleDetailsTicket = (ticket, expected) => {
    if (expected.is_sold_section) {
        const headers = [...ticket.querySelectorAll(".text-large.text-center.text-bold")];
        const soldHeader = headers.find((h) => normalizeText(h.textContent) === "SOLD:");
        expect(Boolean(soldHeader)).toBe(true);
    } else if (expected.is_sold_section === false) {
        const headers = [...ticket.querySelectorAll(".text-large.text-center.text-bold")];
        const soldHeader = headers.find((h) => normalizeText(h.textContent) === "SOLD:");
        expect(Boolean(soldHeader)).toBe(false);
    }

    if (expected.is_refund_section) {
        const headers = [...ticket.querySelectorAll(".text-large.text-center.text-bold")];
        const refundHeader = headers.find((h) => normalizeText(h.textContent) === "REFUNDED:");
        expect(Boolean(refundHeader)).toBe(true);
    } else if (expected.is_refund_section === false) {
        const headers = [...ticket.querySelectorAll(".text-large.text-center.text-bold")];
        const refundHeader = headers.find((h) => normalizeText(h.textContent) === "REFUNDED:");
        expect(Boolean(refundHeader)).toBe(false);
    }

    if (expected.payments) {
        for (const payment of expected.payments) {
            expect(normalizeText(ticket.textContent)).toInclude(payment.name);
        }
    }

    if (expected.taxes) {
        for (const tax of expected.taxes) {
            expect(normalizeText(ticket.textContent)).toInclude(tax.name);
        }
    }

    if (expected.total_paid) {
        expect(normalizeText(ticket.textContent)).toInclude(expected.total_paid);
    }
};

export const expectCashMoveTicket = (ticket, expected) => {
    if (expected.logo) {
        const logo = ticket.querySelector("div[name='logo'] img");
        expect(Boolean(logo)).toBe(true, {
            message: "Ticket should have a logo image",
        });
    } else if (expected.logo === false) {
        const logo = ticket.querySelector("div[name='logo'] img");
        expect(Boolean(logo)).toBe(false, {
            message: "Ticket should not have a logo image",
        });
    }

    if (expected.type) {
        const typeEl = [...ticket.querySelectorAll(".text-center.text-large")].find((el) =>
            normalizeText(el.textContent).includes("CASH")
        );
        expect(Boolean(typeEl)).toBe(true, {
            message: "Ticket should have CASH type element",
        });
        expect(normalizeText(typeEl.textContent)).toInclude(expected.type);
    }

    if (expected.amount) {
        const rows = [...ticket.querySelectorAll("table tbody tr")];
        const amountRow = rows.find((r) => normalizeText(r.textContent).includes("AMOUNT"));
        expect(Boolean(amountRow)).toBe(true, {
            message: "Ticket should have AMOUNT row",
        });
        expect(normalizeText(amountRow.textContent)).toInclude(expected.amount);
    }

    if (expected.reason) {
        const rows = [...ticket.querySelectorAll("table tbody tr")];
        const reasonRow = rows.find((r) => normalizeText(r.textContent).includes("REASON"));
        expect(Boolean(reasonRow)).toBe(true, {
            message: "Ticket should have REASON row",
        });
        expect(normalizeText(reasonRow.textContent)).toInclude(expected.reason);
    }

    if (expected.date) {
        const dateEl = ticket.querySelector(".text-large.text-center");
        expect(Boolean(dateEl)).toBe(true, {
            message: "Ticket should have date element",
        });
        expect(normalizeText(dateEl.textContent)).toInclude(expected.date);
    }

    if (expected.is_company_info) {
        const companyInfo = ticket.querySelector("tbody[name='company_info']");
        expect(Boolean(companyInfo)).toBe(true, {
            message: "Ticket should have company info section",
        });
    } else if (expected.is_company_info === false) {
        expect(Boolean(ticket.querySelector("tbody[name='company_info']"))).toBe(false, {
            message: "Ticket should not have company info section",
        });
    }
};

export const expectTipTicket = (ticket, expected) => {
    if (expected.logo) {
        const logo = ticket.querySelector("div[name='logo'] img");
        expect(Boolean(logo)).toBe(true, {
            message: "Ticket should have a logo image",
        });
    } else if (expected.logo === false) {
        const logo = ticket.querySelector("div[name='logo'] img");
        expect(Boolean(logo)).toBe(false, {
            message: "Ticket should not have a logo image",
        });
    }

    if (expected.title) {
        const titleEl = ticket.querySelector(".text-large.text-center.text-bold");
        expect(Boolean(titleEl)).toBe(true, {
            message: "Ticket should have a title element",
        });
        expect(normalizeText(titleEl.textContent)).toInclude(expected.title);
    }

    if (expected.name) {
        const nameEl = ticket.querySelector(".pos-payment-terminal-receipt");
        expect(Boolean(nameEl)).toBe(true, {
            message: "Ticket should have a name/terminal receipt element",
        });
        expect(normalizeText(nameEl.textContent)).toInclude(expected.name);
    } else if (expected.name === false) {
        expect(Boolean(ticket.querySelector(".pos-payment-terminal-receipt"))).toBe(false, {
            message: "Ticket should not have a name element when name is empty",
        });
    }

    if (expected.subtotal_amount) {
        const subtotalRow = ticket.querySelector("td[name='subtotal']");
        expect(Boolean(subtotalRow)).toBe(true, {
            message: "Ticket should have subtotal row",
        });
        const subtotalValue = subtotalRow.parentElement.querySelector("td:last-child");
        expect(normalizeText(subtotalValue.textContent)).toInclude(expected.subtotal_amount);
    }

    if (expected.total_amount) {
        const totalEl = ticket.querySelector(".total-amount");
        expect(Boolean(totalEl)).toBe(true, {
            message: "Ticket should have total-amount element",
        });
        expect(normalizeText(totalEl.textContent)).toInclude(expected.total_amount);
    }

    if (expected.is_tip_line) {
        const tables = [...ticket.querySelectorAll("table.mb-3")];
        const tipTable = tables.find((t) => normalizeText(t.textContent).includes("Tip:"));
        expect(Boolean(tipTable)).toBe(true, {
            message: "Ticket should have Tip line with blank space",
        });
    }

    if (expected.is_signature_line) {
        const tables = [...ticket.querySelectorAll("table.mb-3")];
        const sigTable = tables.find((t) => normalizeText(t.textContent).includes("Signature:"));
        expect(Boolean(sigTable)).toBe(true, {
            message: "Ticket should have Signature line",
        });
    }

    if (expected.is_company_info) {
        const companyInfo = ticket.querySelector("tbody[name='company_info']");
        expect(Boolean(companyInfo)).toBe(true, {
            message: "Ticket should have company info section",
        });
    } else if (expected.is_company_info === false) {
        expect(Boolean(ticket.querySelector("tbody[name='company_info']"))).toBe(false, {
            message: "Ticket should not have company info section",
        });
    }
};

export const setTipAfterPaymentConfig = (store) => {
    store.config.iface_tipproduct = true;
    store.config.set_tip_after_payment = true;
    store.config.tip_percentage_1 = 15;
    store.config.tip_percentage_2 = 20;
    store.config.tip_percentage_3 = 25;
};
