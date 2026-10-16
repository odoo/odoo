import { expect } from "@odoo/hoot";

export const expectLoyaltyReceiptPayload = (data, expected) => {
    if (expected.loyaltyPointsData !== undefined) {
        expect(data.extra_data.loyalties).toMatchObject(expected.loyaltyPointsData);
    }
};

export const expectLoyaltyTicketData = (ticket, expected) => {
    if (expected.loyaltyPointsData !== undefined) {
        const loyaltyLines = [...ticket.querySelectorAll(".loyalty")];
        expect(loyaltyLines).toHaveLength(expected.loyaltyPointsData.length);
        loyaltyLines.forEach((line, index) => {
            const expectedLine = expected.loyaltyPointsData[index];
            expect(line.querySelector(".text-start").textContent).toBe(
                expectedLine.name + " " + expectedLine.type
            );
            expect(line.querySelector(".text-end").textContent).toBe(
                expectedLine.points.toString()
            );
        });
    }
};
